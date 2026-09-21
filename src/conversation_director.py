"""
Conversation Director for Telugu Animated Stories
Manages conversational dynamics, active listening responses,
speaker gestures, emotional reaction shots, and shot transitions.
"""

class ConversationDirector:
    """
    Coordinates multi-actor dialogue turns, active listener behavior,
    emotional beats, and camera shot selection.
    """
    def __init__(self):
        # Emotion to gesture / reaction mappings
        self.emotion_reactions = {
            "angry": {"speaker_gesture": "angry", "listener_reaction": "surprised", "camera": "speaker_closeup"},
            "scold": {"speaker_gesture": "angry", "listener_reaction": "sad", "camera": "speaker_closeup"},
            "sad": {"speaker_gesture": "sad", "listener_reaction": "sad", "camera": "medium_character"},
            "cry": {"speaker_gesture": "cry", "listener_reaction": "sad", "camera": "speaker_closeup"},
            "happy": {"speaker_gesture": "happy", "listener_reaction": "happy", "camera": "medium_two_shot"},
            "surprised": {"speaker_gesture": "surprised", "listener_reaction": "surprised", "camera": "reaction_closeup"},
            "pray": {"speaker_gesture": "pray", "listener_reaction": "listen", "camera": "medium_character"},
            "shiver": {"speaker_gesture": "shiver", "listener_reaction": "shiver", "camera": "medium_character"},
            "warm_hands": {"speaker_gesture": "warm_hands", "listener_reaction": "listen", "camera": "medium_character"},
            "cook": {"speaker_gesture": "cook", "listener_reaction": "listen", "camera": "medium_character"},
            "meditate": {"speaker_gesture": "meditate", "listener_reaction": "pray", "camera": "medium_character"}
        }

    def direct_dialogue(self, speaker: str, text: str, emotion: str = "neutral",
                        action_override: str = None, camera_override: str = None,
                        actors: dict = None) -> dict:
        speaker = speaker.lower()
        emotion = emotion.lower() if emotion else "neutral"
        
        # Determine primary speaker action
        if action_override and action_override not in ["speaking", "auto"]:
            speaker_action = action_override.lower()
        elif emotion in self.emotion_reactions:
            speaker_action = self.emotion_reactions[emotion]["speaker_gesture"]
        else:
            speaker_action = "talk"
            
        # Determine camera shot
        if camera_override and camera_override not in ["auto", "default"]:
            shot = camera_override.lower()
        elif emotion in self.emotion_reactions:
            shot = self.emotion_reactions[emotion]["camera"]
        elif speaker == "narrator":
            shot = "wide"
        else:
            shot = "medium_character"
            
        # Plan listener reactions for all non-speaking actors currently present
        listener_states = {}
        if actors:
            for actor_id, actor in actors.items():
                if actor_id != speaker and actor.get("is_present", True):
                    if speaker_action in ["angry", "scold"]:
                        listener_action = "sad"
                    elif speaker_action in ["surprised", "shock"]:
                        listener_action = "surprised"
                    elif speaker_action in ["cry"]:
                        listener_action = "sad"
                    elif speaker_action in ["pray", "meditate"]:
                        listener_action = "listen"
                    elif actor.get("action") in ["cook", "use_stove", "warm_hands"]:
                        listener_action = actor.get("action")
                    else:
                        listener_action = "listen"
                        
                    listener_states[actor_id] = {
                        "action": listener_action,
                        "facing_speaker": True
                    }
                    
        return {
            "speaker": speaker,
            "speaker_action": speaker_action,
            "camera_shot": shot,
            "listener_states": listener_states
        }
