"""
Storyboard Planner for Telugu Animated Stories
Parses full raw Telugu story transcriptions or narratives into
structured, cinematic screenplays with scenes, character staging,
actions, emotions, dynamic camera framing, and environmental effects.
"""

import re
import os
import json

class StoryboardPlanner:
    """
    Transforms raw Telugu story text into structured cinematic screenplay scenes.
    """
    def __init__(self):
        # Character regex mappings
        self.char_map = {
            r'(శారద|అత్తగారు|అత్తయ్య|అత్త)': 'atha',
            r'(అనామిక|కోడలు|పేద కోడలు)': 'kodalu',
            r'(సరోజ)': 'saroja',
            r'(పద్మ)': 'padma',
            r'(సుధాకర్)': 'sudhakar',
            r'(మహర్షి|ఋషి|ముని)': 'maharshi',
            r'(రమేష్|భర్త)': 'ramesh',
            r'(ప్రసాద్|మామగారు|తాతయ్య)': 'prasad',
            r'(హరీష్|బాబీ|కొడుకు)': 'harish',
            r'(భవ్య|పాప|కూతురు)': 'bhavya',
            r'(కాంతమ్మ)': 'kanthamma'
        }
        
        # Location keywords -> backgrounds
        self.loc_keywords = [
            (['అరుగు', 'వరండా', 'ఇంటి బయట', 'వాకిట్లో'], 'village_winter_porch'),
            (['సరోజ ఇంటికి', 'వీధి', 'రోడ్డు', 'దారిలో', 'సుధాకర్ ఇంటికి', 'నడుస్తూ'], 'village_street_night'),
            (['చెరువు', 'చెట్టు', 'మహర్షి', 'ధ్యానం', 'చెట్టు కింద'], 'lake_tree_night'),
            (['వంటగది', 'పొయ్యి', 'వంట', 'మాయా పొయ్యి'], 'village_winter_kitchen'),
            (['బెడ్రూమ్', 'హీటర్', 'లాప్‌టాప్', 'పట్నం', 'రూమ్'], 'city_bedroom_heater'),
            (['స్టోర్ రూమ్', 'చలి గది', 'గదిలో'], 'store_room_cold')
        ]

    def detect_emotion_and_action(self, text: str) -> tuple:
        """Infers emotion and physical action from Telugu words."""
        text_l = text.lower()
        
        if any(w in text_l for w in ['వణుకుతూ', 'చలికి', 'చలిగా', 'మంచు']):
            return 'shiver', 'shiver'
        elif any(w in text_l for w in ['కోపంగా', 'విసుగ్గా', 'గట్టిగా అరిచి', 'తిడుతూ']):
            return 'angry', 'angry'
        elif any(w in text_l for w in ['కన్నీళ్లు', 'ఏడుస్తూ', 'బాధపడుతూ', 'కష్టాలు']):
            return 'cry', 'cry'
        elif any(w in text_l for w in ['ఆశ్చర్యంగా', 'అద్భుతం', 'కళ్లు పెద్దవి']):
            return 'surprised', 'surprised'
        elif any(w in text_l for w in ['సంతోషంగా', 'ఆనందంగా', 'నవ్వుతూ']):
            return 'happy', 'happy'
        elif any(w in text_l for w in ['నమస్కరించి', 'దండం', 'ప్రార్థిస్తూ', 'వేడుకుంటూ']):
            return 'pray', 'pray'
        elif any(w in text_l for w in ['ధ్యానం', 'ప్రశాంతంగా', 'కళ్లు మూసుకుని']):
            return 'meditate', 'meditate'
        elif any(w in text_l for w in ['తలుపు కొట్టింది', 'తలుపు మీద కొట్టి']):
            return 'neutral', 'knock_door'
        elif any(w in text_l for w in ['తలుపు తీసింది', 'తలుపు తెరిచింది']):
            return 'neutral', 'open_door'
        elif any(w in text_l for w in ['వంట చేస్తూ', 'పొయ్యి మీద', 'కలుపుతూ']):
            return 'happy', 'cook'
        elif any(w in text_l for w in ['చలిమంట', 'చేతులు కాచుకుంటూ']):
            return 'neutral', 'warm_hands'
        elif any(w in text_l for w in ['నడుస్తూ', 'బయలుదేరింది', 'వెళ్ళింది']):
            return 'neutral', 'walk'
        elif any(w in text_l for w in ['తీసుకుని', 'ఎత్తుకుని']):
            return 'neutral', 'carry'
        elif any(w in text_l for w in ['తింటూ', 'భోజనం']):
            return 'happy', 'eat'
            
        return 'neutral', 'speaking'

    def parse_story(self, text: str, story_title: str = "Telugu Animated Story") -> dict:
        """
        Parses continuous narrative text into screenplay scenes.
        """
        # Split text into logical sentences / phrases
        sentences = [s.strip() for s in re.split(r'[.!?।
]+', text) if len(s.strip()) > 8]
        
        scenes = []
        current_scene = None
        current_bg = None
        
        for idx, sentence in enumerate(sentences):
            # 1. Determine Location
            detected_bg = None
            for kw_list, bg in self.loc_keywords:
                if any(kw in sentence for kw in kw_list):
                    detected_bg = bg
                    break
                    
            if not detected_bg and not current_bg:
                detected_bg = 'village_winter_porch'
            elif not detected_bg:
                detected_bg = current_bg
                
            # Start new scene if location changed or current scene has reached capacity
            if detected_bg != current_bg or not current_scene or len(current_scene['dialogues']) >= 6:
                if current_scene and current_scene['dialogues']:
                    scenes.append(current_scene)
                    
                current_bg = detected_bg
                effects = ['snow'] if 'winter' in current_bg or 'street' in current_bg or 'lake' in current_bg else []
                if 'kitchen' in current_bg:
                    effects.append('steam')
                    
                current_scene = {
                    'scene_id': len(scenes) + 1,
                    'background': current_bg,
                    'effect': ', '.join(effects) if effects else '',
                    'dialogues': []
                }
                
            # 2. Determine Speaker
            speaker = 'narrator'
            for pattern, char_id in self.char_map.items():
                if re.search(pattern, sentence):
                    # If sentence mentions character and has direct dialogue indicators
                    if any(q in sentence for q in ['అంది', 'అన్నాడు', 'అంటూ', 'చెప్పింది', 'చెప్పాడు', 'అడిగింది', 'అడిగాడు', 'వచ్చావ్', 'ఏంటి', 'ఎందుకు']):
                        speaker = char_id
                        break
                        
            emotion, action = self.detect_emotion_and_action(sentence)
            
            # Camera framing logic
            if speaker == 'narrator':
                cam = 'wide'
            elif emotion in ['angry', 'cry', 'surprised']:
                cam = 'speaker_closeup'
            elif action in ['walk', 'knock_door', 'open_door']:
                cam = 'follow_walk' if action == 'walk' else 'medium_character'
            else:
                cam = 'medium_character'
                
            current_scene['dialogues'].append({
                'character': speaker,
                'text': sentence,
                'emotion': emotion,
                'action': action,
                'camera': cam
            })
            
        if current_scene and current_scene['dialogues']:
            scenes.append(current_scene)
            
        return {
            'title': story_title,
            'scenes': scenes
        }
