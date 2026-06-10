import json

# Эффекты для каждой сцены (mood-based)
EFFECTS = {
    "tension": {
        "zoom": 1.15,
        "speed": 0.85,
        "color": "saturate=1.3",
        "brightness": "brightness=0.9"
    },
    "calm": {
        "zoom": 1.05,
        "speed": 1.0,
        "color": "saturate=0.8",
        "brightness": "brightness=1.05"
    },
    "shock": {
        "zoom": 1.25,
        "speed": 0.7,
        "color": "saturate=1.5",
        "brightness": "brightness=0.8"
    },
    "revelation": {
        "zoom": 1.1,
        "speed": 0.9,
        "color": "saturate=1.2",
        "brightness": "brightness=1.1"
    },
    "sad": {
        "zoom": 1.0,
        "speed": 1.1,
        "color": "hue=20:saturate=0.5",
        "brightness": "brightness=0.85"
    }
}

def get_effects_for_scene(scene_description):
    """Определяет эффекты на основе описания сцены"""
    scene_lower = scene_description.lower()
    
    if any(word in scene_lower for word in ["напряжение", "страх", "ужас", "опасность"]):
        return "tension"
    elif any(word in scene_lower for word in ["спокойно", "мирно", "тихо", "шепот"]):
        return "calm"
    elif any(word in scene_lower for word in ["шок", "удар", "внезапно", "вдруг"]):
        return "shock"
    elif any(word in scene_lower for word in ["открытие", "истина", "раскрытие", "понимание"]):
        return "revelation"
    elif any(word in scene_lower for word in ["грусть", "печаль", "плач", "боль", "смерть"]):
        return "sad"
    else:
        return "calm"

def generate_effects_filter(image_idx, effect_type, duration_per_image):
    """Генерирует ffmpeg фильтр для эффекта"""
    effect = EFFECTS[effect_type]
    
    zoom = effect["zoom"]
    speed = effect["speed"]
    
    # Zoom фильтр
    zoom_filter = f"[{image_idx}:v]scale=iw*{zoom}:ih*{zoom},crop=1080:1920:((iw-1080)/2):((ih-1920)/2)"
    
    # Цвет и яркость
    zoom_filter += f",{effect['color']},{effect['brightness']}"
    
    # Скорость (замедление/ускорение)
    zoom_filter += f",setpts=N\\/(30*{speed})/TB"
    
    zoom_filter += f"[v{image_idx}]"
    
    return zoom_filter, effect_type
