from app.db.models import TextTemplate

# Cache to store templates and reduce database calls
_template_cache = {}

async def get_template(template_key: str, default_text: str = None) -> str:
    """
    Get text template from MongoDB or return the default text if not found.
    Templates are cached for better performance.
    """
    # Check if the template is in cache
    if template_key in _template_cache:
        return _template_cache[template_key]
    
    # Try to get template from database
    template = await TextTemplate.find_one({"template_key": template_key})
    
    if template:
        # Store in cache and return
        _template_cache[template_key] = template.template_text
        return template.template_text
    elif default_text:
        # Template not found, but we have default text
        # Store the default in MongoDB for future editing
        await TextTemplate(
            template_key=template_key,
            template_text=default_text,
            description=f"Auto-created template for {template_key}"
        ).save()
        
        # Add to cache
        _template_cache[template_key] = default_text
        return default_text
    else:
        # No template and no default
        return f"MISSING_TEMPLATE:{template_key}"
    

def sync_get_template(template_key: str, default_text: str = None) -> str:
    """
    Synchronous fetch of template from MongoDB for sync contexts.
    """
    from app.db.models import TextTemplate
    global _template_cache
    # Check cache first
    if template_key in _template_cache:
        print(_template_cache[template_key])
        return _template_cache[template_key]

    # Direct sync DB query (assuming TextTemplate uses Motor or PyMongo)
    # If using Motor (async), you need to use PyMongo for sync here
    try:
        from pymongo import MongoClient
        import os
        mongo_url = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
        client = MongoClient(mongo_url)
        db = client.get_database("islobbot-dev")
        collection = db["text_templates"]
        template = collection.find_one({"template_key": template_key})
        if template and "template_text" in template:
            _template_cache[template_key] = template["template_text"]
            return template["template_text"]
        elif default_text:
            # Insert default template for future editing
            collection.insert_one({
                "template_key": template_key,
                "template_text": default_text,
                "description": f"Auto-created template for {template_key}"
            })
            _template_cache[template_key] = default_text
            return default_text
        else:
            return f"MISSING_TEMPLATE:{template_key}"
    except Exception as e:
        return f"ERROR_SYNC_TEMPLATE:{template_key}:{e}"


async def format_template(template_key: str, default_text: str = None, **kwargs) -> str:
    """
    Get template and format it with the provided keyword arguments
    """
    template = await get_template(template_key, default_text)
    return template.format(**kwargs)

def clear_template_cache():
    """Clear the template cache to force reloading from database"""
    global _template_cache
    _template_cache = {}
