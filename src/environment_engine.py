"""
Environment and Atmospheric FX Engine for Telugu Animated Stories
Renders reusable natural and magical particle systems:
snow, rain, cooking steam, fire glow, and magical sparkles.
"""

import math
import numpy as np
from PIL import Image, ImageDraw

class EnvironmentEngine:
    def __init__(self, width: int = 1920, height: int = 1080):
        self.width = width
        self.height = height
        np.random.seed(42)
        
        # 1. Snow particles
        self.snow_particles = []
        for _ in range(70):
            self.snow_particles.append({
                'x': float(np.random.uniform(0, width)),
                'y': float(np.random.uniform(0, height)),
                'r': float(np.random.uniform(2.5, 6.0)),
                'vy': float(np.random.uniform(1.8, 3.8)),
                'phase': float(np.random.uniform(0, 2 * math.pi)),
                'alpha': int(np.random.uniform(140, 220))
            })
            
        # 2. Magic golden sparkles
        self.magic_particles = []
        for _ in range(35):
            self.magic_particles.append({
                'dx': float(np.random.uniform(-140, 140)),
                'speed': float(np.random.uniform(2.2, 4.8)),
                'lifetime': int(np.random.uniform(30, 55)),
                'offset': int(np.random.uniform(0, 55)),
                'r': float(np.random.uniform(3.0, 7.0)),
                'color': (255, int(np.random.uniform(200, 255)), int(np.random.uniform(60, 120)))
            })
            
        # 3. Cooking steam particles
        self.steam_particles = []
        for _ in range(25):
            self.steam_particles.append({
                'dx': float(np.random.uniform(-30, 30)),
                'speed': float(np.random.uniform(1.2, 2.8)),
                'lifetime': int(np.random.uniform(40, 70)),
                'offset': int(np.random.uniform(0, 70)),
                'r': float(np.random.uniform(12.0, 24.0))
            })

    def render(self, frame_img: Image.Image, frame_idx: int, effects: list):
        if not effects:
            return
            
        overlay = Image.new('RGBA', (self.width, self.height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        
        for eff in effects:
            eff_type = eff.lower()
            
            if eff_type == 'snow':
                for p in self.snow_particles:
                    y = (p['y'] + frame_idx * p['vy']) % self.height
                    x = (p['x'] + math.sin(frame_idx * 0.035 + p['phase']) * 22) % self.width
                    r = p['r']
                    draw.ellipse([x - r, y - r, x + r, y + r], fill=(255, 255, 255, p['alpha']))
                    
            elif eff_type == 'magic':
                origin_x, origin_y = 480, 720
                for p in self.magic_particles:
                    age = (frame_idx + p['offset']) % p['lifetime']
                    frac = age / float(p['lifetime'])
                    y = origin_y - frac * 300
                    x = origin_x + p['dx'] * math.sin(frac * math.pi)
                    alpha = int((1.0 - frac) * 230)
                    r = p['r'] * (1.0 - 0.4 * frac)
                    c = p['color'] + (alpha,)
                    draw.ellipse([x - r, y - r, x + r, y + r], fill=c)
                    
            elif eff_type in ['steam', 'cooking_steam']:
                origin_x, origin_y = 450, 680
                for p in self.steam_particles:
                    age = (frame_idx + p['offset']) % p['lifetime']
                    frac = age / float(p['lifetime'])
                    y = origin_y - frac * 180
                    x = origin_x + p['dx'] + math.sin(frac * 3.0) * 15
                    alpha = int((1.0 - frac) * 60) # soft translucent steam
                    r = p['r'] * (1.0 + 0.8 * frac)
                    draw.ellipse([x - r, y - r, x + r, y + r], fill=(240, 240, 250, alpha))
                    
        frame_img.alpha_composite(overlay)
