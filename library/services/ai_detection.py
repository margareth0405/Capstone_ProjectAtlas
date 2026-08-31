"""Transparent, local writing-pattern indicators for AI Detection."""

import re
from statistics import pstdev


class WritingPatternAnalyzer:
    """Calculate explainable writing-pattern indicators for one text sample."""

    word_pattern = re.compile(r"[A-Za-z]+(?:'[A-Za-z]+)?")
    sentence_pattern = re.compile(r"[.!?]+")

    def analyze(self, text):
        words = self.word_pattern.findall(text.lower())
        sentences = [
            segment.strip()
            for segment in self.sentence_pattern.split(text)
            if segment.strip()
        ]
        sentence_lengths = [
            len(self.word_pattern.findall(sentence)) for sentence in sentences
        ]
        word_count = len(words)
        lexical_diversity = len(set(words)) / word_count if word_count else 0
        average_length = (
            sum(sentence_lengths) / len(sentence_lengths) if sentence_lengths else 0
        )
        length_variation = (
            pstdev(sentence_lengths) / average_length
            if len(sentence_lengths) > 1 and average_length
            else 0
        )
        trigrams = list(zip(words, words[1:], words[2:]))
        repeated_phrase_ratio = (
            1 - (len(set(trigrams)) / len(trigrams)) if trigrams else 0
        )
        score = self._score(
            lexical_diversity=lexical_diversity,
            length_variation=length_variation,
            repeated_phrase_ratio=repeated_phrase_ratio,
        )
        label, tone = self._classification(score)
        return {
            "score": score,
            "label": label,
            "tone": tone,
            "word_count": word_count,
            "sentence_count": len(sentences),
            "lexical_diversity": round(lexical_diversity * 100, 1),
            "sentence_variation": round(length_variation * 100, 1),
            "repeated_phrase_ratio": round(repeated_phrase_ratio * 100, 1),
        }

    @staticmethod
    def _score(*, lexical_diversity, length_variation, repeated_phrase_ratio):
        raw_score = (
            20
            + (1 - min(lexical_diversity, 1)) * 35
            + (1 - min(length_variation, 1)) * 25
            + min(repeated_phrase_ratio, 1) * 20
        )
        return max(0, min(100, round(raw_score)))

    @staticmethod
    def _classification(score):
        if score >= 70:
            return "High AI-like indicators", "high"
        if score >= 40:
            return "Mixed indicators", "mixed"
        return "Low AI-like indicators", "low"
