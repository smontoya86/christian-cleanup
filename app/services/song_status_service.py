from ..models import AnalysisResult, Whitelist, Blacklist # Assuming models are in parent dir

class SongStatus:
    def __init__(self, song, analysis_result=None, is_whitelisted=False, is_blacklisted=False, is_preferred=False):
        self.song = song
        self.analysis_result = analysis_result
        self.is_whitelisted = is_whitelisted
        self.is_blacklisted = is_blacklisted
        self.is_preferred = is_preferred # Passed from route
        self._determine_status_properties()

    def _check_purity_flags(self):
        """Helper to check purity flags and return if any are 'High' and the color class."""
        if self.analysis_result:
            purity_flags_attributes = [
                'profanity_degree',
                'sexual_degree',
                'violence_degree',
                'hate_speech_degree',
                'substance_abuse_degree',
                'non_christian_spiritual_degree'
            ]
            for attr_name in purity_flags_attributes:
                flag_value = getattr(self.analysis_result, attr_name, None)
                if flag_value == "High":
                    return True, "bg-danger text-white" # High concern if any purity flag is High
        return False, "" # No high purity flags triggered

    def _determine_status_properties(self):
        # 0. User Preferred (takes precedence over analysis if set by user)
        if self.is_preferred:
            self._message = "User Preferred"
            self._color_class = "bg-info text-dark" # Distinct color for user preferred
            return

        # 1. Whitelisted / Blacklisted (overrides analysis)
        if self.is_whitelisted:
            self._message = "Whitelisted"
            self._color_class = "bg-success text-white"
            return
        if self.is_blacklisted:
            self._message = "Blacklisted"
            self._color_class = "bg-danger text-white"
            return

        # 2. No Analysis Result
        if not self.analysis_result:
            self._message = "Not Analyzed"
            self._color_class = "bg-secondary text-white"
            return

        # 3. Analysis Result exists, check purity flags first
        purity_triggered, purity_color = self._check_purity_flags()
        if purity_triggered:
            self._message = "High Concern (Flag)" # Clarify it's flag-based
            self._color_class = purity_color
            return # High purity concern is a definitive status

        # 4. Analysis Result exists, no high purity flags, check score
        if self.analysis_result.score is None:
            self._message = "Pending Score"
            self._color_class = "bg-info text-dark"
            return

        # Convert the score to a 0-1 scale if needed (assuming score is 0-100)
        score = self.analysis_result.score / 100.0 if self.analysis_result.score > 1 else self.analysis_result.score
        # Score is not None here
        if score >= 0.75:
            self._message = "Low Concern"
            self._color_class = "bg-success text-white"
        elif score >= 0.5:
            self._message = "Medium Concern"
            self._color_class = "bg-warning text-dark"
        else: # score < 0.5
            self._message = "High Concern (Score)" # Clarify it's score-based
            self._color_class = "bg-danger text-white"

    @property
    def display_message(self):
        return self._message

    @property
    def color_class(self):
        return self._color_class
