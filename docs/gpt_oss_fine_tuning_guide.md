# 🎯 GPT-OSS Fine-Tuning Guide (Legacy Documentation)

**Version**: 2.0 (Updated January 2025)
**Status**: SUPERSEDED - See `docs/unified_implementation_plan.md` for current plan
**Strategy**: Knowledge Distillation (Teacher-Student)
**Teacher Model**: Qwen3-8B-Instruct (local fine-tuning)
**Student Model**: OpenAI gpt-oss-20b (knowledge distillation)
**Hardware**: Apple M1 Max (64GB RAM) - Local Deployment
**Scope**: Universal Music Analysis with Christian Evaluation Criteria

---

## ⚠️ IMPORTANT: This document has been superseded

**Please refer to `docs/unified_implementation_plan.md` for the current, consolidated implementation plan.**

This file is maintained for reference but the active development follows the unified plan.

---

## 📋 Project Overview

This guide details the hybrid approach using knowledge distillation to create a superior music analysis system. We first fine-tune Qwen3-8B as a teacher model, then use knowledge distillation to train GPT-OSS-20B as the production student model. This strategy combines the training efficiency of smaller models with the superior capabilities of larger models.

### **Key Objectives:**
- **Phase 1**: Fine-tune Qwen3-8B teacher model (local M1 Max training)
- **Phase 2**: Use knowledge distillation to train GPT-OSS-20B student model
- **Phase 3**: Deploy single GPT-OSS-20B model to replace 4-model HuggingFace system
- Maintain superior accuracy on Christian content while improving secular analysis
- Achieve local deployment with zero ongoing API costs
- Enable offline operation with open weights

### **Success Metrics:**
- **Christian Accuracy**: ≥95 score on verified Christian content
- **Secular Improvement**: 30%+ better analysis quality vs current system
- **Speed**: <3 seconds per song analysis
- **Cost**: Zero ongoing API costs (local inference)
- **Coverage**: 100K training songs across 15+ genres

### **🎯 CURRENT STATUS & STRATEGY UPDATE (January 2025):**

**✅ STRATEGIC DECISION - KNOWLEDGE DISTILLATION APPROACH:**
1. **Teacher Model**: Qwen3-8B-Instruct (8.2B parameters) - proven M1 Max compatibility
2. **Student Model**: GPT-OSS-20B (20.9B parameters) - superior NLP capabilities for production
3. **Training Strategy**: Local teacher training → Knowledge distillation → Production deployment
4. **Memory Feasibility**: Qwen3-8B ~20-25GB vs GPT-OSS-20B ~45-60GB (distillation solves this)
5. **Quality Strategy**: Leverage Qwen3 latest tech + GPT-OSS production power
6. **Cost Strategy**: Local training + local inference = $0 monthly costs

**📊 KEY TECHNICAL FINDINGS:**
- **Base Model**: `unsloth/gpt-oss-20b-BF16` (43GB downloaded and working)
- **Training Approach**: LoRA fine-tuning with PyTorch (CPU inference slow but training viable)
- **Memory Optimization**: FP32 precision, gradient accumulation, small batch sizes
- **Data Strategy**: Option A (11.2K API songs) validation → Option B (66.2K hybrid collection)
- **API Sources**: 4 viable providers identified (Genius, LRCLib, OpenAPIHub, FabriXAPI)

**📈 DATA COLLECTION CAPACITY (Updated after testing):**
- **Option A (Validation)**: 2,000-3,500 songs from legitimate APIs (2-3 days)
  - Genius: 1,000-2,000 songs ✅ | LRCLib: 1,000-1,500 songs ✅ | Manual curation: 500 songs
- **Option B (Production)**: 66,200 songs with hybrid approach (8-10 days)
  - API Collection: 3,500 songs | Web Scraping: 55,000 songs | Additional sources: 7,700 songs

**⚠️ KNOWN LIMITATIONS:**
- CPU inference extremely slow (minutes per token) - training only, not production inference
- 100K target reduced to 66.2K based on available legitimate sources
- Web scraping required for Option B (rate limiting essential)

---

## 🎯 IMPLEMENTATION STRATEGY: OPTION A → OPTION B

### **Option A: API-Only Validation Phase (UPDATED)**
**Timeline**: 2-3 days | **Target**: 2,000-3,500 songs | **Purpose**: Validate fine-tuning pipeline

**Phase A.1: Enhanced API Collection (Days 1-2)**
1. Genius API: Artist-focused collection (1,000-2,000 songs)
   - Expand to 100+ diverse artists across all genres
   - Implement lyrics extraction from URLs
   - Focus on prolific songwriters and popular tracks
2. LRCLib: Optimized keyword search (1,000-1,500 songs)
   - Use highest-performing search terms from testing
   - Genre-specific keywords for better coverage
   - Enhanced deduplication across results

**Phase A.2: Quality Enhancement (Day 2)**
1. Manual curation (300-500 songs)
   - High-value Christian songs for accuracy validation
   - Genre representatives for comprehensive coverage
   - Popular tracks for relevance testing
2. Working dataset validation
   - Research Kaggle and academic datasets
   - Test additional open-source repositories

**Phase A.3: Training Dataset Generation (Day 3)**
1. Annotate collected songs with current HuggingFace system
2. Format dataset for GPT-OSS-20B training (OpenAI chat format)
3. Split into train/validation sets (90/10): 1,800-3,150 / 200-350 songs
4. Quality validation: Christian accuracy, genre coverage, lyrics length

**Phase A.4: Validation Training (Day 3)**
1. Run memory-optimized LoRA training (2-4 hours on M1 Max)
2. Test inference quality with focus on Christian content accuracy (target: 95%+)
3. Compare performance against current 4-model system
4. Document results and validate pipeline before Option B scaling

### **Option B: Hybrid Production Phase (After A Validation)**
**Timeline**: 8-10 days | **Target**: 66,200 songs | **Purpose**: Full production training

**Phase B.1: Web Scraping Implementation (Days 1-3)**
1. Implement ethical scrapers for 4 target sites
2. Rate limiting (1-2 req/sec per site)
3. Anti-detection measures and error handling
4. Test collection capacity

**Phase B.2: Large-Scale Collection (Days 4-7)**
1. Parallel collection from all sources
2. Real-time deduplication and quality checks
3. Progress monitoring and error recovery
4. Target: 55,000 additional songs

**Phase B.3: Production Training (Days 8-10)**
1. Generate full training dataset (66.2K songs)
2. Extended LoRA fine-tuning with production parameters
3. Comprehensive evaluation and testing
4. Model deployment preparation

---

## 🖥️ Hardware Validation & Setup

### **Task 1.1: M1 Max Compatibility Verification** ✅ COMPLETED

**Acceptance Criteria:**
- [x] ~~MLX framework successfully loads gpt-oss-20b model~~ → **DECISION**: Using PyTorch/Transformers instead (MLX lacks gpt_oss support)
- [x] Model fits in 64GB unified memory with quantization → **CONFIRMED**: 20.9B parameters load successfully, ~38GB needed
- [ ] ~~Inference speed <5 seconds per song on M1 Max~~ → **FINDING**: CPU inference very slow (training focus only)
- [x] Training setup supports gradient accumulation for large batches → **CONFIRMED**: LoRA + gradient accumulation working

**✅ ACTUAL RESULTS:**
- **Hardware**: M1 Max 64GB RAM is sufficient for LoRA training
- **Framework**: PyTorch + PEFT + Transformers (not MLX due to architecture incompatibility)
- **Model Loading**: `unsloth/gpt-oss-20b-BF16` loads successfully (20.9B parameters)
- **Memory Usage**: ~38GB for FP32 training, 42GB available = ✅ FEASIBLE
- **LoRA Config**: Rank 16, 7 target modules = 1.99M trainable params (0.01%)

**TDD Implementation:**
```python
# test_m1_max_setup.py
def test_mlx_model_loading():
    """Test MLX can load and run gpt-oss-20b on M1 Max"""
    import mlx.core as mx
    from mlx_lm import load, generate

    # Load model with MLX (optimized for Apple Silicon)
    model, tokenizer = load("openai/gpt-oss-20b")

    # Test basic inference
    test_prompt = "Analyze this Christian song: Amazing Grace how sweet the sound"
    response = generate(model, tokenizer, prompt=test_prompt, max_tokens=100)

    assert len(response) > len(test_prompt)
    assert isinstance(response, str)

def test_memory_efficiency():
    """Verify 64GB RAM is sufficient for training"""
    import psutil
    import mlx.core as mx

    # Check available memory
    available_memory = psutil.virtual_memory().available / (1024**3)
    assert available_memory >= 50, f"Need 50GB+ free RAM, got {available_memory:.1f}GB"

    # Test model loading doesn't exceed memory
    initial_memory = psutil.virtual_memory().used / (1024**3)
    model, tokenizer = load("openai/gpt-oss-20b")
    final_memory = psutil.virtual_memory().used / (1024**3)

    memory_used = final_memory - initial_memory
    assert memory_used < 30, f"Model uses too much memory: {memory_used:.1f}GB"

def test_training_setup():
    """Test LoRA training configuration on M1 Max"""
    from mlx_lm.tuners.lora import LoRALinear

    # Configure LoRA for memory efficiency
    lora_config = {
        "rank": 16,
        "alpha": 32,
        "dropout": 0.1,
        "target_modules": ["q_proj", "v_proj", "k_proj", "o_proj"]
    }

    # Test LoRA adapter creation
    adapter = LoRALinear(input_dims=4096, output_dims=4096, **lora_config)

    # Verify trainable parameters <1% of total
    trainable_params = sum(p.size for p in adapter.parameters() if p.requires_grad)
    total_params = 20_000_000_000  # 20B parameters

    efficiency_ratio = trainable_params / total_params
    assert efficiency_ratio < 0.01, f"LoRA should train <1% params, got {efficiency_ratio:.2%}"
```

**Subtasks:**
1. Install MLX framework for Apple Silicon optimization
2. Configure quantization settings for 20B model
3. Set up LoRA adapters for memory-efficient training
4. Verify gradient accumulation for large effective batch sizes

---

## 📊 Training Data Collection & Curation

### **🎯 PHASE APPROACH DECISION:**
**Option A (Current)**: Quick test with 100 songs (validate approach)
**Option B (Future)**: Full production with 100K songs (after Option A success)

### **Task 2.1: Multi-Provider Data Collection Pipeline**

**Option A Acceptance Criteria (CURRENT FOCUS):**
- [ ] 100 total songs collected (20 Christian, 80 secular across genres)
- [ ] Rate limiting: 1 request/sec per provider (strict compliance)
- [ ] Data quality >90% (lyrics present, accurate metadata)
- [ ] Manual curation for quality assurance
- [ ] Test all 3 providers: Genius, MusixMatch, LyricsGenius

**Option B Acceptance Criteria (DEFERRED):**
- [ ] 100,000 total songs collected across all genres
- [ ] 5,000-10,000 verified Christian songs included
- [ ] Rate limiting prevents API abuse (1 req/sec per provider)
- [ ] Data quality >90% (lyrics present, accurate metadata)
- [ ] Genre distribution covers 15+ musical categories

**TDD Implementation:**
```python
# test_data_collection.py
def test_multi_provider_collection():
    """Test collection from Genius, MusixMatch, LyricsGenius APIs"""
    from data_collectors import GeniusCollector, MusixMatchCollector, LyricsGeniusCollector

    target_count = 100000
    providers = [
        GeniusCollector(rate_limit=1.0),
        MusixMatchCollector(rate_limit=1.0),
        LyricsGeniusCollector(rate_limit=1.0)
    ]

    total_collected = 0
    for provider in providers:
        batch_size = target_count // len(providers)
        songs = provider.collect_songs(
            count=batch_size,
            genres=["pop", "rock", "hip-hop", "country", "christian", "metal",
                   "folk", "electronic", "r&b", "jazz", "blues", "indie",
                   "alternative", "punk", "reggae"],
            quality_threshold=0.9
        )

        total_collected += len(songs)

        # Verify quality
        lyrics_present = sum(1 for song in songs if song.lyrics)
        quality_ratio = lyrics_present / len(songs)
        assert quality_ratio >= 0.9, f"Quality too low: {quality_ratio:.1%}"

    assert total_collected >= target_count, f"Collected {total_collected}, need {target_count}"

def test_christian_content_curation():
    """Test Christian music identification and curation"""
    christian_songs = collect_christian_content(
        sources=["christian_music_archive", "ccli_database", "worship_together"],
        min_count=5000,
        max_count=10000
    )

    # Verify Christian content quality
    for song in christian_songs[:100]:  # Sample validation
        analysis = verify_christian_content(song)
        assert analysis.confidence >= 0.8, f"Low confidence Christian content: {song.title}"
        assert any(theme in analysis.themes for theme in
                  ["Christ-Centered", "Gospel", "Worship", "Prayer", "Biblical"]), \
               f"No Christian themes found: {song.title}"

    assert 5000 <= len(christian_songs) <= 10000, f"Christian count: {len(christian_songs)}"

def test_genre_distribution():
    """Test balanced genre representation"""
    all_songs = load_collected_songs()
    genre_counts = count_by_genre(all_songs)

    target_genres = [
        "pop", "rock", "hip-hop", "country", "christian", "metal", "folk",
        "electronic", "r&b", "jazz", "blues", "indie", "alternative",
        "punk", "reggae", "classical", "world"
    ]

    total_songs = len(all_songs)
    for genre in target_genres:
        count = genre_counts.get(genre, 0)
        percentage = count / total_songs

        # Each genre should have reasonable representation
        if genre == "christian":
            assert percentage >= 0.05, f"Christian underrepresented: {percentage:.1%}"
        else:
            assert percentage >= 0.02, f"{genre} underrepresented: {percentage:.1%}"

    assert len(genre_counts) >= 15, f"Only {len(genre_counts)} genres, need 15+"
```

**Subtasks:**
1. Set up API credentials for all 3 lyrical providers
2. Implement rate limiting (1 request/second per provider)
3. Build genre-balanced collection strategy
4. Create data validation and quality checks
5. Implement deduplication across providers
6. Set up data storage and indexing system

### **Task 2.2: Training Data Annotation Pipeline**

**Acceptance Criteria:**
- [ ] Current HuggingFace system generates consistent annotations
- [ ] Training format matches OpenAI chat completion standard
- [ ] Annotations include all framework elements (score, themes, scripture)
- [ ] Quality validation catches annotation errors >95% accuracy
- [ ] Train/validation split maintains genre balance

**TDD Implementation:**
```python
# test_annotation_pipeline.py
def test_annotation_consistency():
    """Test current system generates consistent annotations"""
    from app.services.unified_analysis_service import UnifiedAnalysisService

    analyzer = UnifiedAnalysisService()
    test_songs = load_test_songs(sample_size=100)

    # Generate annotations twice for consistency check
    annotations_1 = []
    annotations_2 = []

    for song in test_songs:
        ann1 = analyzer.analysis_service.analyze_song(song)
        ann2 = analyzer.analysis_service.analyze_song(song)

        annotations_1.append(ann1)
        annotations_2.append(ann2)

    # Check consistency (scores should be within 5 points)
    score_differences = []
    for ann1, ann2 in zip(annotations_1, annotations_2):
        diff = abs(ann1.get_final_score() - ann2.get_final_score())
        score_differences.append(diff)

    avg_difference = sum(score_differences) / len(score_differences)
    assert avg_difference <= 5, f"Inconsistent scoring: avg diff {avg_difference:.1f}"

def test_training_format_generation():
    """Test conversion to OpenAI training format"""
    sample_songs = load_sample_songs(1000)
    training_examples = []

    for song in sample_songs:
        # Generate analysis with current system
        analysis = current_system.analyze_song(song)

        # Convert to training format
        training_example = {
            "messages": [
                {
                    "role": "system",
                    "content": "You are an expert music analyst specializing in Christian content evaluation. Analyze songs across all genres using biblical standards."
                },
                {
                    "role": "user",
                    "content": f"Analyze this song:\n\nTitle: {song.title}\nArtist: {song.artist}\nGenre: {song.genre}\nLyrics: {song.lyrics}\n\nProvide a comprehensive analysis including score, concern level, biblical themes, and supporting scripture."
                },
                {
                    "role": "assistant",
                    "content": format_analysis_response(analysis)
                }
            ]
        }

        training_examples.append(training_example)

    # Validate format
    for example in training_examples:
        assert len(example["messages"]) == 3
        assert example["messages"][0]["role"] == "system"
        assert example["messages"][1]["role"] == "user"
        assert example["messages"][2]["role"] == "assistant"

        assistant_content = example["messages"][2]["content"]
        assert "score" in assistant_content.lower()
        assert "concern" in assistant_content.lower()
        assert "biblical" in assistant_content.lower() or "christian" in assistant_content.lower()

def test_train_validation_split():
    """Test balanced train/validation split"""
    all_annotations = load_all_annotations()

    train_data, val_data = split_data(all_annotations, train_ratio=0.8)

    # Check size
    assert len(train_data) / len(all_annotations) == 0.8
    assert len(val_data) / len(all_annotations) == 0.2

    # Check genre balance maintained
    train_genres = count_genres(train_data)
    val_genres = count_genres(val_data)
    all_genres = count_genres(all_annotations)

    for genre in all_genres:
        train_ratio = train_genres[genre] / all_genres[genre]
        val_ratio = val_genres[genre] / all_genres[genre]

        # Ratios should be close to target (within 5%)
        assert 0.75 <= train_ratio <= 0.85, f"{genre} train ratio: {train_ratio:.2f}"
        assert 0.15 <= val_ratio <= 0.25, f"{genre} val ratio: {val_ratio:.2f}"
```

**Subtasks:**
1. Run current system on all 100K collected songs
2. Generate training examples in OpenAI chat format
3. Implement quality validation checks
4. Create balanced train/validation split (80/20)
5. Generate JSONL files for training
6. Create annotation statistics and quality reports

---

## 🔧 Fine-Tuning Infrastructure

### **Task 3.1: MLX Fine-Tuning Setup**

**Acceptance Criteria:**
- [ ] MLX-LM configured for gpt-oss-20b fine-tuning
- [ ] LoRA adapters reduce trainable parameters to <1%
- [ ] Gradient accumulation enables large effective batch sizes
- [ ] Training pipeline handles 100K examples efficiently
- [ ] Checkpointing and resuming works correctly

**TDD Implementation:**
```python
# test_mlx_training_setup.py
def test_mlx_lora_configuration():
    """Test LoRA configuration for efficient training"""
    from mlx_lm.tuners.lora import LoRA
    from mlx_lm import load

    model, tokenizer = load("openai/gpt-oss-20b")

    # Configure LoRA
    lora_config = {
        "rank": 16,
        "alpha": 32,
        "dropout": 0.1,
        "target_modules": ["self_attn.q_proj", "self_attn.v_proj",
                          "self_attn.k_proj", "self_attn.o_proj"]
    }

    lora_model = LoRA(model, **lora_config)

    # Count trainable parameters
    trainable = sum(p.size for p in lora_model.trainable_parameters())
    total = sum(p.size for p in model.parameters())

    efficiency = trainable / total
    assert efficiency < 0.01, f"LoRA efficiency: {efficiency:.3%}, target <1%"

    # Test gradient computation
    dummy_input = mx.random.uniform(shape=(1, 100))
    output = lora_model(dummy_input)
    assert output.shape[0] == 1, "Model output shape incorrect"

def test_data_loading_pipeline():
    """Test efficient data loading for large datasets"""
    from mlx_lm.utils import load_dataset

    # Load training data
    train_data = load_dataset("train_annotations.jsonl")
    val_data = load_dataset("val_annotations.jsonl")

    assert len(train_data) >= 80000, f"Train data too small: {len(train_data)}"
    assert len(val_data) >= 20000, f"Val data too small: {len(val_data)}"

    # Test batch loading
    batch_size = 4
    batches = list(train_data.batch(batch_size))

    assert len(batches[0]) == batch_size
    assert all("messages" in example for example in batches[0])

def test_training_configuration():
    """Test training hyperparameters and setup"""
    training_config = {
        "learning_rate": 2e-4,
        "batch_size": 4,
        "grad_accumulation_steps": 16,  # Effective batch size: 64
        "max_seq_length": 2048,
        "num_epochs": 3,
        "warmup_steps": 500,
        "save_steps": 1000,
        "eval_steps": 500,
    }

    # Validate learning rate for LoRA
    assert 1e-5 <= training_config["learning_rate"] <= 5e-4, "LR out of range for LoRA"

    # Validate effective batch size
    effective_batch = training_config["batch_size"] * training_config["grad_accumulation_steps"]
    assert effective_batch >= 32, f"Effective batch too small: {effective_batch}"

    # Validate sequence length for model
    assert training_config["max_seq_length"] <= 4096, "Sequence length too long for model"
```

**Subtasks:**
1. Install MLX-LM framework on M1 Max
2. Configure LoRA adapters for memory efficiency
3. Set up gradient accumulation for large effective batches
4. Implement data loading and preprocessing pipeline
5. Configure training hyperparameters
6. Set up checkpointing and model saving

### **Task 3.2: Training Execution Pipeline**

**Acceptance Criteria:**
- [ ] Training runs stably without memory errors
- [ ] Loss decreases consistently over epochs
- [ ] Validation metrics improve during training
- [ ] Checkpoints save and resume correctly
- [ ] Training completes in reasonable time (<48 hours)

**TDD Implementation:**
```python
# test_training_execution.py
def test_training_stability():
    """Test training runs without crashes or memory issues"""
    from mlx_lm.tuners.lora import LoRA
    from mlx_lm import load
    import mlx.core as mx
    import mlx.nn as nn

    model, tokenizer = load("openai/gpt-oss-20b")
    lora_model = LoRA(model, rank=16, alpha=32)

    # Load small subset for testing
    train_data = load_training_subset(size=100)

    optimizer = mx.optimizers.Adam(learning_rate=2e-4)

    # Test training loop
    losses = []
    for epoch in range(3):
        epoch_losses = []

        for batch in train_data.batch(2):
            # Forward pass
            loss = compute_loss(lora_model, batch, tokenizer)
            epoch_losses.append(float(loss))

            # Backward pass
            grads = mx.grad(compute_loss)(lora_model, batch, tokenizer)
            optimizer.update(lora_model, grads)

            # Check for NaN/Inf
            assert not mx.isnan(loss), f"NaN loss detected: {loss}"
            assert not mx.isinf(loss), f"Inf loss detected: {loss}"

        avg_loss = sum(epoch_losses) / len(epoch_losses)
        losses.append(avg_loss)

    # Loss should generally decrease
    assert losses[-1] < losses[0], f"Loss not decreasing: {losses[0]:.3f} -> {losses[-1]:.3f}"

def test_validation_evaluation():
    """Test validation metrics during training"""
    val_data = load_validation_subset(size=50)

    # Test evaluation function
    val_metrics = evaluate_model(lora_model, val_data, tokenizer)

    required_metrics = ["perplexity", "accuracy", "christian_accuracy", "avg_score_error"]
    for metric in required_metrics:
        assert metric in val_metrics, f"Missing metric: {metric}"
        assert isinstance(val_metrics[metric], (int, float)), f"Invalid {metric} type"

    # Christian accuracy should be high
    assert val_metrics["christian_accuracy"] >= 0.9, f"Low Christian accuracy: {val_metrics['christian_accuracy']:.2f}"

def test_checkpoint_functionality():
    """Test model saving and loading"""
    checkpoint_path = "./test_checkpoint"

    # Save model
    lora_model.save_weights(checkpoint_path)

    # Load model
    loaded_model, _ = load("openai/gpt-oss-20b")
    loaded_lora = LoRA(loaded_model, rank=16, alpha=32)
    loaded_lora.load_weights(checkpoint_path)

    # Test inference consistency
    test_input = "Analyze this Christian song: Amazing Grace"
    tokens = tokenizer.encode(test_input)

    original_output = lora_model.generate(mx.array(tokens), max_tokens=50)
    loaded_output = loaded_lora.generate(mx.array(tokens), max_tokens=50)

    # Outputs should be identical
    assert mx.array_equal(original_output, loaded_output), "Checkpoint loading failed"
```

**Subtasks:**
1. Implement training loop with MLX
2. Set up loss computation for chat completion
3. Configure validation evaluation during training
4. Implement checkpoint saving and resuming
5. Add training monitoring and logging
6. Set up early stopping based on validation metrics

---

## 📈 Evaluation Framework

### **Task 4.1: Comprehensive Evaluation Suite**

**Acceptance Criteria:**
- [ ] Christian content maintains ≥95 score accuracy
- [ ] Secular music shows 30%+ improvement over current system
- [ ] Hallucination rate <10% on edge cases
- [ ] Inference speed <3 seconds per song
- [ ] Biblical theme detection F1-score ≥0.85

**TDD Implementation:**
```python
# test_evaluation_suite.py
def test_christian_content_accuracy():
    """Test accuracy on verified Christian content"""
    christian_test_set = load_christian_benchmark_songs()  # 500+ verified songs

    correct_predictions = 0
    for song in christian_test_set:
        result = fine_tuned_model.analyze(song)

        # Christian songs should score ≥95
        if song.verified_christian and result.score >= 95:
            correct_predictions += 1
        elif not song.verified_christian and result.score < 95:
            correct_predictions += 1

    accuracy = correct_predictions / len(christian_test_set)
    assert accuracy >= 0.95, f"Christian accuracy: {accuracy:.2%}, need ≥95%"

def test_secular_improvement():
    """Test improvement on secular content vs current system"""
    secular_test_set = load_secular_benchmark_songs()  # 1000+ songs across genres

    improvements = 0
    for song in secular_test_set:
        # Get current system result
        current_result = current_system.analyze(song)

        # Get fine-tuned result
        fine_tuned_result = fine_tuned_model.analyze(song)

        # Calculate improvement metrics
        improvement = calculate_improvement_score(current_result, fine_tuned_result, song)

        if improvement > 0.1:  # 10% improvement threshold
            improvements += 1

    improvement_rate = improvements / len(secular_test_set)
    assert improvement_rate >= 0.3, f"Improvement rate: {improvement_rate:.1%}, need ≥30%"

def test_hallucination_detection():
    """Test for reduced hallucinations on edge cases"""
    edge_cases = load_edge_case_songs()  # Ambiguous, instrumental, etc.

    hallucinations = 0
    for song in edge_cases:
        result = fine_tuned_model.analyze(song)

        # Check for specific hallucination patterns
        if detect_biblical_hallucination(result, song):
            hallucinations += 1
        elif detect_theme_hallucination(result, song):
            hallucinations += 1
        elif detect_scripture_hallucination(result, song):
            hallucinations += 1

    hallucination_rate = hallucinations / len(edge_cases)
    assert hallucination_rate < 0.1, f"Hallucination rate: {hallucination_rate:.1%}, need <10%"

def test_inference_speed():
    """Test inference speed on M1 Max"""
    test_songs = load_speed_test_songs(100)

    times = []
    for song in test_songs:
        start_time = time.time()
        result = fine_tuned_model.analyze(song)
        end_time = time.time()

        times.append(end_time - start_time)

    avg_time = sum(times) / len(times)
    p95_time = sorted(times)[int(0.95 * len(times))]

    assert avg_time < 3.0, f"Avg inference: {avg_time:.1f}s, need <3s"
    assert p95_time < 5.0, f"P95 inference: {p95_time:.1f}s, need <5s"

def test_biblical_theme_detection():
    """Test F1-score on biblical theme detection"""
    theme_test_set = load_theme_labeled_songs()  # 500+ songs with expert labels

    true_positives = 0
    false_positives = 0
    false_negatives = 0

    for song in theme_test_set:
        predicted_themes = set(fine_tuned_model.analyze(song).biblical_themes)
        actual_themes = set(song.expert_labeled_themes)

        tp = len(predicted_themes & actual_themes)
        fp = len(predicted_themes - actual_themes)
        fn = len(actual_themes - predicted_themes)

        true_positives += tp
        false_positives += fp
        false_negatives += fn

    precision = true_positives / (true_positives + false_positives)
    recall = true_positives / (true_positives + false_negatives)
    f1_score = 2 * (precision * recall) / (precision + recall)

    assert f1_score >= 0.85, f"F1-score: {f1_score:.2f}, need ≥0.85"
```

**Subtasks:**
1. Create Christian content benchmark dataset
2. Build secular music improvement evaluation
3. Implement hallucination detection algorithms
4. Set up performance benchmarking on M1 Max
5. Create biblical theme detection evaluation
6. Build comprehensive evaluation dashboard

### **Task 4.2: Comparative Analysis**

**Acceptance Criteria:**
- [ ] Side-by-side comparison with current 4-model system
- [ ] Cost analysis shows 100% API cost elimination
- [ ] Speed comparison demonstrates improvement
- [ ] Quality metrics match or exceed current system
- [ ] Error analysis identifies improvement areas

**TDD Implementation:**
```python
# test_comparative_analysis.py
def test_system_comparison():
    """Compare fine-tuned model vs current 4-model system"""
    comparison_dataset = load_balanced_comparison_set(2000)  # Balanced across genres

    current_results = []
    fine_tuned_results = []

    for song in comparison_dataset:
        # Current system (4 HuggingFace models)
        current_start = time.time()
        current_result = current_system.analyze(song)
        current_time = time.time() - current_start

        # Fine-tuned system (1 custom model)
        fine_tuned_start = time.time()
        fine_tuned_result = fine_tuned_model.analyze(song)
        fine_tuned_time = time.time() - fine_tuned_start

        current_results.append({
            "result": current_result,
            "time": current_time,
            "cost": estimate_api_cost(current_result)
        })

        fine_tuned_results.append({
            "result": fine_tuned_result,
            "time": fine_tuned_time,
            "cost": 0  # No API cost
        })

    # Compare metrics
    current_accuracy = calculate_overall_accuracy(current_results, comparison_dataset)
    fine_tuned_accuracy = calculate_overall_accuracy(fine_tuned_results, comparison_dataset)

    assert fine_tuned_accuracy >= current_accuracy * 0.95, \
           f"Accuracy regression: {fine_tuned_accuracy:.2%} vs {current_accuracy:.2%}"

    # Speed comparison
    avg_current_time = sum(r["time"] for r in current_results) / len(current_results)
    avg_fine_tuned_time = sum(r["time"] for r in fine_tuned_results) / len(fine_tuned_results)

    speed_improvement = (avg_current_time - avg_fine_tuned_time) / avg_current_time
    assert speed_improvement > 0, f"Speed regression: {speed_improvement:.1%}"

    # Cost comparison (should be 100% reduction)
    total_current_cost = sum(r["cost"] for r in current_results)
    total_fine_tuned_cost = sum(r["cost"] for r in fine_tuned_results)

    assert total_fine_tuned_cost == 0, f"Expected zero cost, got ${total_fine_tuned_cost:.2f}"
    assert total_current_cost > 0, "Current system should have API costs"

def test_error_analysis():
    """Analyze errors and improvement opportunities"""
    error_analysis_set = load_challenging_songs(500)

    error_categories = {
        "false_positive_christian": [],
        "false_negative_christian": [],
        "score_overestimate": [],
        "score_underestimate": [],
        "theme_misclassification": [],
        "scripture_mismatch": []
    }

    for song in error_analysis_set:
        result = fine_tuned_model.analyze(song)
        ground_truth = song.expert_annotation

        # Categorize errors
        if result.score >= 95 and ground_truth.score < 80:
            error_categories["false_positive_christian"].append((song, result))
        elif result.score < 80 and ground_truth.score >= 95:
            error_categories["false_negative_christian"].append((song, result))

        score_diff = abs(result.score - ground_truth.score)
        if score_diff > 20:
            if result.score > ground_truth.score:
                error_categories["score_overestimate"].append((song, result))
            else:
                error_categories["score_underestimate"].append((song, result))

    # Error rates should be low
    for category, errors in error_categories.items():
        error_rate = len(errors) / len(error_analysis_set)
        assert error_rate < 0.05, f"High {category} rate: {error_rate:.1%}"
```

**Subtasks:**
1. Build balanced comparison dataset
2. Implement side-by-side evaluation pipeline
3. Create cost analysis framework
4. Develop error categorization system
5. Generate comparative performance reports
6. Create improvement recommendations

---

## 🚀 Deployment & Integration

### **Task 5.1: Model Integration**

**Acceptance Criteria:**
- [ ] Fine-tuned model replaces HuggingFace analyzer in production
- [ ] API interface maintains backward compatibility
- [ ] Model loads efficiently on application startup
- [ ] Batch processing works for playlist analysis
- [ ] Error handling gracefully manages edge cases

**TDD Implementation:**
```python
# test_model_integration.py
def test_analyzer_replacement():
    """Test replacing HuggingFaceAnalyzer with fine-tuned model"""
    from app.services.analyzer_cache import AnalyzerCache

    # Create new analyzer with fine-tuned model
    fine_tuned_analyzer = FineTunedGPTOSSAnalyzer(
        model_path="./fine-tuned-gpt-oss-20b",
        device="mps"  # M1 Max GPU
    )

    # Test interface compatibility
    test_song = {
        "title": "Amazing Grace",
        "artist": "Traditional",
        "lyrics": "Amazing grace how sweet the sound that saved a wretch like me..."
    }

    result = fine_tuned_analyzer.analyze_song(test_song)

    # Verify output format matches current system
    assert hasattr(result, 'score'), "Missing score attribute"
    assert hasattr(result, 'concern_level'), "Missing concern_level attribute"
    assert hasattr(result, 'biblical_themes'), "Missing biblical_themes attribute"
    assert hasattr(result, 'supporting_scripture'), "Missing supporting_scripture attribute"

    # Verify value ranges
    assert 0 <= result.score <= 100, f"Score out of range: {result.score}"
    assert result.concern_level in ["Very Low", "Low", "Medium", "High", "Critical"]
    assert isinstance(result.biblical_themes, list)
    assert isinstance(result.supporting_scripture, list)

def test_batch_processing():
    """Test batch processing for playlist analysis"""
    test_songs = load_test_playlist(50)

    # Test batch analysis
    start_time = time.time()
    results = fine_tuned_analyzer.analyze_songs_batch(test_songs)
    batch_time = time.time() - start_time

    # Compare to sequential processing
    sequential_start = time.time()
    sequential_results = []
    for song in test_songs:
        result = fine_tuned_analyzer.analyze_song(song)
        sequential_results.append(result)
    sequential_time = time.time() - sequential_start

    # Batch should be faster or comparable
    assert len(results) == len(test_songs)
    assert batch_time <= sequential_time * 1.2, f"Batch slower: {batch_time:.1f}s vs {sequential_time:.1f}s"

    # Results should be equivalent
    for batch_result, sequential_result in zip(results, sequential_results):
        score_diff = abs(batch_result.score - sequential_result.score)
        assert score_diff <= 2, f"Batch/sequential score difference: {score_diff}"

def test_startup_performance():
    """Test model loading time on startup"""
    start_time = time.time()

    analyzer = FineTunedGPTOSSAnalyzer(
        model_path="./fine-tuned-gpt-oss-20b",
        device="mps"
    )

    load_time = time.time() - start_time

    # Should load within reasonable time
    assert load_time < 30, f"Model loading too slow: {load_time:.1f}s"

    # Test immediate inference
    test_result = analyzer.analyze_song({
        "title": "Test",
        "artist": "Test",
        "lyrics": "This is a test song"
    })

    assert test_result is not None
    assert hasattr(test_result, 'score')

def test_error_handling():
    """Test graceful error handling"""
    analyzer = FineTunedGPTOSSAnalyzer("./fine-tuned-gpt-oss-20b")

    # Test empty lyrics
    result = analyzer.analyze_song({
        "title": "No Lyrics",
        "artist": "Test",
        "lyrics": ""
    })

    assert result is not None
    assert result.score >= 0  # Should handle gracefully

    # Test very long lyrics
    long_lyrics = "La la la " * 10000  # Very long text
    result = analyzer.analyze_song({
        "title": "Long Song",
        "artist": "Test",
        "lyrics": long_lyrics
    })

    assert result is not None
    assert result.score >= 0

    # Test malformed input
    try:
        result = analyzer.analyze_song(None)
        assert False, "Should raise exception for None input"
    except Exception as e:
        assert isinstance(e, (ValueError, TypeError))
```

**Subtasks:**
1. Create FineTunedGPTOSSAnalyzer class
2. Implement analyzer cache integration
3. Update unified analysis service
4. Test batch processing optimization
5. Implement graceful error handling
6. Update application configuration

### **Task 5.2: Production Deployment**

**Acceptance Criteria:**
- [ ] Docker configuration updated for fine-tuned model
- [ ] Model artifacts properly packaged and versioned
- [ ] Rollback mechanism available to previous system
- [ ] Monitoring and logging capture performance metrics
- [ ] Documentation updated for new model

**TDD Implementation:**
```python
# test_production_deployment.py
def test_docker_configuration():
    """Test Docker setup for fine-tuned model"""
    # Build Docker image with fine-tuned model
    build_result = subprocess.run([
        "docker", "build", "-t", "christian-curator:fine-tuned",
        "--build-arg", "MODEL_PATH=./fine-tuned-gpt-oss-20b",
        "."
    ], capture_output=True, text=True)

    assert build_result.returncode == 0, f"Docker build failed: {build_result.stderr}"

    # Test container startup
    run_result = subprocess.run([
        "docker", "run", "-d", "--name", "test-curator",
        "-p", "5001:5001", "christian-curator:fine-tuned"
    ], capture_output=True, text=True)

    assert run_result.returncode == 0, f"Container start failed: {run_result.stderr}"

    # Test health check
    time.sleep(10)  # Allow startup time
    health_result = subprocess.run([
        "curl", "-f", "http://localhost:5001/health"
    ], capture_output=True, text=True)

    assert health_result.returncode == 0, "Health check failed"

    # Cleanup
    subprocess.run(["docker", "stop", "test-curator"])
    subprocess.run(["docker", "rm", "test-curator"])

def test_model_versioning():
    """Test model versioning and artifact management"""
    model_version = get_model_version()
    model_path = f"./models/gpt-oss-christian-music-v{model_version}"

    # Check model artifacts exist
    required_files = [
        "adapter_config.json",
        "adapter_model.bin",
        "tokenizer.json",
        "tokenizer_config.json",
        "model_config.json"
    ]

    for file_name in required_files:
        file_path = os.path.join(model_path, file_name)
        assert os.path.exists(file_path), f"Missing model file: {file_name}"

    # Test version metadata
    with open(os.path.join(model_path, "version_info.json")) as f:
        version_info = json.load(f)

    required_metadata = [
        "version", "training_date", "base_model", "training_data_size",
        "validation_metrics", "christian_accuracy", "secular_improvement"
    ]

    for field in required_metadata:
        assert field in version_info, f"Missing version metadata: {field}"

def test_rollback_mechanism():
    """Test ability to rollback to previous system"""
    # Backup current configuration
    backup_config = backup_current_config()

    # Deploy fine-tuned model
    deploy_fine_tuned_model()

    # Test rollback
    rollback_to_previous_system()

    # Verify rollback worked
    current_analyzer = get_current_analyzer()
    assert isinstance(current_analyzer, HuggingFaceAnalyzer), "Rollback failed"

    # Test analysis still works
    test_result = current_analyzer.analyze_song({
        "title": "Test",
        "artist": "Test",
        "lyrics": "Test lyrics"
    })

    assert test_result is not None
    assert hasattr(test_result, 'score')

    # Restore fine-tuned model
    deploy_fine_tuned_model()

def test_monitoring_integration():
    """Test monitoring and logging for fine-tuned model"""
    # Test performance metrics collection
    metrics = collect_performance_metrics(duration_minutes=5)

    required_metrics = [
        "avg_inference_time", "requests_per_minute", "error_rate",
        "memory_usage", "cpu_usage", "christian_accuracy", "avg_score"
    ]

    for metric in required_metrics:
        assert metric in metrics, f"Missing metric: {metric}"
        assert isinstance(metrics[metric], (int, float)), f"Invalid {metric} type"

    # Test error logging
    error_logs = get_recent_error_logs(hours=1)

    # Should have structured error information
    for log_entry in error_logs:
        assert "timestamp" in log_entry
        assert "error_type" in log_entry
        assert "song_id" in log_entry or "context" in log_entry
```

**Subtasks:**
1. Update Docker configuration for fine-tuned model
2. Implement model versioning and artifact management
3. Create rollback mechanism to previous system
4. Set up monitoring for fine-tuned model performance
5. Update deployment scripts and documentation
6. Create production deployment checklist

---

## 📊 Success Metrics & Validation

### **Final Acceptance Criteria:**

1. **Performance Metrics:**
   - [ ] Christian content accuracy ≥95% (scores ≥95 for verified Christian songs)
   - [ ] Secular music improvement ≥30% over current system
   - [ ] Inference speed <3 seconds per song on M1 Max
   - [ ] Hallucination rate <10% on edge cases
   - [ ] Biblical theme F1-score ≥0.85

2. **Technical Metrics:**
   - [ ] Model size <20GB on disk with adapters
   - [ ] Memory usage <30GB during inference
   - [ ] Training completed successfully on 100K songs
   - [ ] Zero API costs (100% local inference)
   - [ ] Batch processing 50+ songs efficiently

3. **Integration Metrics:**
   - [ ] Seamless replacement of 4-model system
   - [ ] Backward compatible API interface
   - [ ] Production deployment successful
   - [ ] Rollback mechanism validated
   - [ ] Monitoring and logging operational

### **Deliverables:**

1. **Model Artifacts:**
   - Fine-tuned gpt-oss-20b with LoRA adapters
   - Model configuration and tokenizer files
   - Version metadata and training logs

2. **Code Updates:**
   - FineTunedGPTOSSAnalyzer implementation
   - Updated unified analysis service
   - Modified analyzer cache system
   - Updated Docker configuration

3. **Documentation:**
   - Fine-tuning process documentation
   - Model performance evaluation report
   - Deployment and rollback procedures
   - Updated system architecture documentation

4. **Evaluation Reports:**
   - Comprehensive performance comparison
   - Christian content accuracy validation
   - Secular music improvement analysis
   - Cost savings analysis

---

## 🔄 Continuous Improvement

### **Post-Deployment Monitoring:**

1. **Performance Tracking:**
   - Monitor inference speed and memory usage
   - Track Christian content accuracy in production
   - Measure user satisfaction with analysis quality

2. **Model Updates:**
   - Collect new training data from user interactions
   - Retrain model periodically with improved data
   - A/B test model improvements before deployment

3. **Error Analysis:**
   - Track and categorize analysis errors
   - Identify patterns in misclassified content
   - Update training data to address error patterns

This comprehensive plan provides a complete roadmap for fine-tuning OpenAI's gpt-oss-20b model specifically for your Christian music analysis use case, with detailed TDD implementation and clear acceptance criteria for each phase.
