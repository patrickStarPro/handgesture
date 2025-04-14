class RuleBasedTranslator:
    """
    A simple rule-based translator for sign language gestures.
    """

    def translate(self, detected_signs):
        """
        Translates a sequence of detected signs into a sentence.

        Args:
            detected_signs (list): A list of detected gestures (e.g., ["HELLO", "YES"]).

        Returns:
            str: A translated sentence.
        """
        if not detected_signs:
            return "No signs detected."

        # Join detected signs into a sentence
        return " ".join(detected_signs)