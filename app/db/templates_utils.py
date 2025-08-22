from app.db.models import TextTemplate
from typing import Dict, Any

_template_cache = {}

async def get_template(template_key: str, default_text: str = None) -> str:
    if template_key in _template_cache:
        return _template_cache[template_key]

    template = await TextTemplate.find_one({"template_key": template_key})
    
    if template:
        _template_cache[template_key] = template.template_text
        return template.template_text
    elif default_text:
        await TextTemplate(
            template_key=template_key,
            template_text=default_text,
            description=f"Auto-created text for {template_key}"
        ).save()
        
        _template_cache[template_key] = default_text
        return default_text
    else:
        return f"MISSING_TEMPLATE:{template_key}"

async def format_template(template_key: str, default_text: str = None, **kwargs) -> str:
    template = await get_template(template_key, default_text)
    return template.format(**kwargs)

def clear_template_cache():
    global _template_cache
    _template_cache = {}