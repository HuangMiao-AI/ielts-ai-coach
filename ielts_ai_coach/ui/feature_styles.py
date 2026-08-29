"""Combined CSS fragments for focused feature pages."""

from ielts_ai_coach.ui.guest_writing_styles import GUEST_WRITING_CSS
from ielts_ai_coach.ui.listening_vocabulary_styles import LISTENING_VOCABULARY_CSS


FEATURE_CSS = "\n".join((GUEST_WRITING_CSS, LISTENING_VOCABULARY_CSS))
