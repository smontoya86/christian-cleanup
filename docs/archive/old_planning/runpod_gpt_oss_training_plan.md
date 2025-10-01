# RunPod GPT-OSS-20B Fine-Tuning Implementation Plan

## Overview
Based on comprehensive research, we'll use RunPod.io for cloud-based fine-tuning of GPT-OSS-20B using QLoRA for optimal cost/performance balance.

## Recommended Configuration

### Hardware Selection
- **GPU**: 1x NVIDIA H100 80GB SXM
- **Cost**: $4.47/hour
- **Estimated Training Time**: 8-12 hours
- **Total Cost**: $36-54 (excellent ROI)

### Training Method
- **QLoRA (4-bit quantization + LoRA)**
- **Expected Quality**: 95-99% of full fine-tuning
- **Memory Usage**: ~46GB VRAM (comfortable in 80GB)
- **Training Data**: 1,332 high-quality examples from production dataset

## Step-by-Step Implementation

### Phase 1: RunPod Setup (15 minutes)

1. **Create RunPod Account**
   - Sign up at runpod.io
   - Add payment method
   - Verify account

2. **Deploy Pod**
   - Select "Secure Cloud" for reliability
   - Choose H100 80GB SXM GPU
   - Select PyTorch template: `pytorch/pytorch:2.1.0-cuda12.1-cudnn8-devel`
   - Container disk: 100GB (for model weights + training data)
   - Deploy pod

3. **Connect to Pod**
   - Use SSH connection (more stable than web terminal)
   - Copy SSH command from RunPod console
   - Connect: `ssh root@<pod-ip> -p <port>`

### Phase 2: Environment Setup (20 minutes)

1. **Install Dependencies**
```bash
# Update system
apt update && apt upgrade -y

# Install required packages
pip install transformers==4.36.2
pip install datasets==2.14.7
pip install accelerate==0.25.0
pip install bitsandbytes==0.41.3
pip install peft==0.7.1
pip install trl==0.7.4
pip install scipy
pip install wandb  # for experiment tracking
```

2. **Upload Training Data**
```bash
# Create training directory
mkdir -p /workspace/training_data

# Upload our production training data
# Option A: Use runpodctl (if available locally)
runpodctl send training_data/production/production_train_20250806_1613.jsonl

# Option B: Use wget from cloud storage
wget -O /workspace/training_data/production_train.jsonl \
  "https://your-cloud-storage/production_train.jsonl"

# Option C: Use scp from local machine
scp training_data/production/production_train_20250806_1613.jsonl \
  root@<pod-ip>:/workspace/training_data/production_train.jsonl
```

### Phase 3: Training Script Setup (15 minutes)

Create the training script:

```python
# /workspace/gpt_oss_qlora_training.py
import os
import torch
import json
from datasets import Dataset
from transformers import (
    AutoTokenizer,
    AutoModelForCausalLM,
    TrainingArguments,
    Trainer,
    BitsAndBytesConfig
)
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
from trl import SFTTrainer
import wandb

def setup_qlora_training():
    """Setup QLoRA training for GPT-OSS-20B"""

    # Model configuration
    model_id = "unsloth/gpt-oss-20b-BF16"

    # QLoRA configuration
    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.float16,
        bnb_4bit_use_double_quant=True,
    )

    # Load tokenizer
    tokenizer = AutoTokenizer.from_pretrained(model_id)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    # Load model in 4-bit
    model = AutoModelForCausalLM.from_pretrained(
        model_id,
        quantization_config=bnb_config,
        device_map="auto",
        trust_remote_code=True,
        torch_dtype=torch.float16
    )

    # Prepare for training
    model = prepare_model_for_kbit_training(model)

    # LoRA configuration
    lora_config = LoraConfig(
        r=16,  # rank
        lora_alpha=32,  # alpha
        target_modules=[
            "q_proj", "k_proj", "v_proj", "o_proj",
            "gate_proj", "up_proj", "down_proj"
        ],
        lora_dropout=0.05,
        bias="none",
        task_type="CAUSAL_LM"
    )

    # Apply LoRA
    model = get_peft_model(model, lora_config)

    return model, tokenizer

def load_training_data():
    """Load and format training data"""

    training_data = []
    with open("/workspace/training_data/production_train.jsonl", "r") as f:
        for line in f:
            example = json.loads(line.strip())

            # Convert to text format for SFT
            text = ""
            for message in example["messages"]:
                if message["role"] == "system":
                    text += f"<|system|>{message['content']}"
                elif message["role"] == "user":
                    text += f"<|user|>{message['content']}"
                elif message["role"] == "assistant":
                    text += f"<|assistant|>{message['content']}<|endoftext|>"

            training_data.append({"text": text})

    return Dataset.from_list(training_data)

def main():
    """Main training function"""

    # Initialize wandb for tracking
    wandb.init(
        project="gpt-oss-christian-fine-tuning",
        name="qlora-h100-run-1"
    )

    print("🚀 Starting GPT-OSS-20B QLoRA Fine-tuning")
    print("=" * 50)

    # Setup model and tokenizer
    print("📥 Loading model and tokenizer...")
    model, tokenizer = setup_qlora_training()
    print(f"✅ Model loaded: {model.num_parameters():,} total parameters")
    print(f"📊 Trainable parameters: {model.get_nb_trainable_parameters()}")

    # Load training data
    print("📁 Loading training data...")
    train_dataset = load_training_data()
    print(f"✅ Loaded {len(train_dataset)} training examples")

    # Training arguments
    training_args = TrainingArguments(
        output_dir="/workspace/gpt-oss-christian-qlora",
        per_device_train_batch_size=1,
        gradient_accumulation_steps=8,  # Effective batch size = 8
        num_train_epochs=3,
        max_steps=500,  # Conservative for initial run
        learning_rate=2e-4,
        fp16=True,
        logging_steps=10,
        save_steps=50,
        save_strategy="steps",
        optim="adamw_torch",
        lr_scheduler_type="cosine",
        warmup_steps=50,
        gradient_checkpointing=True,
        dataloader_pin_memory=False,
        remove_unused_columns=False,
        report_to="wandb"
    )

    # Initialize trainer
    trainer = SFTTrainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        tokenizer=tokenizer,
        dataset_text_field="text",
        max_seq_length=512,
        packing=False
    )

    print("🎯 Training Configuration:")
    print(f"   • Method: QLoRA (4-bit + LoRA)")
    print(f"   • GPU: H100 80GB")
    print(f"   • Batch size: {training_args.per_device_train_batch_size}")
    print(f"   • Gradient accumulation: {training_args.gradient_accumulation_steps}")
    print(f"   • Effective batch size: {training_args.per_device_train_batch_size * training_args.gradient_accumulation_steps}")
    print(f"   • Max steps: {training_args.max_steps}")
    print(f"   • Learning rate: {training_args.learning_rate}")
    print(f"   • Expected training time: 8-12 hours")
    print(f"   • Expected cost: $36-54")

    # Start training
    print("\n🚀 Starting training...")
    trainer.train()

    # Save final model
    print("💾 Saving final model...")
    trainer.save_model()
    tokenizer.save_pretrained("/workspace/gpt-oss-christian-qlora")

    print("🎉 Training completed successfully!")
    print("✅ Model saved to: /workspace/gpt-oss-christian-qlora")

    wandb.finish()

if __name__ == "__main__":
    main()
```

### Phase 4: Execute Training (8-12 hours)

1. **Start Training**
```bash
cd /workspace
python gpt_oss_qlora_training.py
```

2. **Monitor Progress**
   - Watch GPU utilization: `nvidia-smi -l 5`
   - Monitor training logs in real-time
   - Track metrics via wandb dashboard

3. **Checkpointing**
   - Training saves every 50 steps
   - Can resume if interrupted: `trainer.train(resume_from_checkpoint=True)`

### Phase 5: Model Validation (30 minutes)

1. **Test Inference**
```python
# test_inference.py
from transformers import AutoTokenizer, AutoModelForCausalLM
from peft import PeftModel
import torch

# Load base model
base_model = AutoModelForCausalLM.from_pretrained(
    "unsloth/gpt-oss-20b-BF16",
    torch_dtype=torch.float16,
    device_map="auto"
)

# Load tokenizer
tokenizer = AutoTokenizer.from_pretrained("unsloth/gpt-oss-20b-BF16")

# Load LoRA weights
model = PeftModel.from_pretrained(base_model, "/workspace/gpt-oss-christian-qlora")

# Test inference
prompt = """<|system|>You are a Christian music analysis system that evaluates music through a Christian worldview...<|user|>Analyze this song for Christian appropriateness:

**Song**: "Amazing Grace" by John Newton
**Lyrics**: Amazing grace how sweet the sound, that saved a wretch like me...

<|assistant|>"""

inputs = tokenizer(prompt, return_tensors="pt")
outputs = model.generate(**inputs, max_length=512, temperature=0.7)
response = tokenizer.decode(outputs[0], skip_special_tokens=True)
print(response)
```

### Phase 6: Model Export & Download (30 minutes)

1. **Merge LoRA with Base Model** (Optional)
```python
# merge_model.py
from transformers import AutoTokenizer, AutoModelForCausalLM
from peft import PeftModel
import torch

# Load and merge
base_model = AutoModelForCausalLM.from_pretrained("unsloth/gpt-oss-20b-BF16")
model = PeftModel.from_pretrained(base_model, "/workspace/gpt-oss-christian-qlora")
merged_model = model.merge_and_unload()

# Save merged model
merged_model.save_pretrained("/workspace/gpt-oss-christian-merged")
tokenizer.save_pretrained("/workspace/gpt-oss-christian-merged")
```

2. **Download Model**
```bash
# Compress for download
tar -czf gpt-oss-christian-qlora.tar.gz gpt-oss-christian-qlora/

# Download options:
# Option A: scp to local machine
scp root@<pod-ip>:/workspace/gpt-oss-christian-qlora.tar.gz ./

# Option B: Upload to cloud storage for later download
# Option C: Keep on RunPod for inference testing
```

## Cost Analysis

### Estimated Costs
- **Setup time**: 1 hour × $4.47 = $4.47
- **Training time**: 10 hours × $4.47 = $44.70
- **Testing/Export**: 1 hour × $4.47 = $4.47
- **Total**: ~$54 (excellent ROI)

### Cost Comparison
- **Local hardware**: Would require $80K+ investment for equivalent
- **Other cloud providers**: 50-100% more expensive
- **Current 4-model system**: Ongoing hosting costs eliminated

## Success Metrics

### Quality Validation
1. **Accuracy on test set**: >95% compared to current system
2. **Theological consistency**: Manual review of 100 test cases
3. **Speed**: Inference time comparable to current 4-model system
4. **Memory efficiency**: Single model vs 4 separate models

### Deployment Readiness
1. **Model size**: Reasonable for local deployment
2. **Inference speed**: <2 seconds per song analysis
3. **Memory usage**: <40GB VRAM for production inference
4. **Integration**: Drop-in replacement for current system

## Risk Mitigation

### Technical Risks
- **Model quality below expectations**: Test with small subset first
- **Memory issues**: Start with smaller batch sizes
- **Training instability**: Use gradient clipping and learning rate scheduling

### Cost Risks
- **Training takes longer**: Set max budget limit ($75)
- **Need multiple attempts**: Budget for 2-3 training runs
- **Model needs iterations**: Each iteration ~$50

## Next Steps After Training

1. **Quality Assessment**: Compare against current 4-model system
2. **Production Integration**: Update Christian Music Curator to use new model
3. **Performance Optimization**: Quantize for faster inference if needed
4. **Documentation**: Update all relevant docs and guides
5. **Monitoring**: Set up production monitoring and fallback systems

## Alternative Configurations

### If QLoRA Quality Insufficient
- **LoRA on 2x A100**: $4.36/hour × 12 hours = $52
- **Full training on 8x A100**: $17.44/hour × 6 hours = $105

### If Budget is Tight
- **A100 80GB QLoRA**: $2.18/hour × 12 hours = $26
- **Spot instances**: Up to 70% discount when available

## Conclusion

This RunPod implementation plan provides:
- **Excellent cost/performance ratio**: $36-54 for production model
- **High success probability**: Proven QLoRA approach
- **Fast iteration**: Complete in 1-2 days
- **Production readiness**: Direct replacement for current system

The investment of <$60 will deliver a custom GPT-OSS-20B model that eliminates ongoing hosting costs while providing superior Christian music analysis capabilities.
