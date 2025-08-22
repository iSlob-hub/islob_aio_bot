from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from app.db.models import TextTemplate, User
from web_app.auth import get_current_user

router = APIRouter(prefix="/api/bot-settings", tags=["bot settings"])

# Список адміністраторів
ADMIN_IDS = [
    "591812219",
    "379872548",
    "5916038251"
]

def get_admin_user(user: User = Depends(get_current_user)) -> User:
    """Dependency to ensure only admin users can access bot settings endpoints"""
    if user.telegram_id not in ADMIN_IDS:
        raise HTTPException(
            status_code=403, 
            detail="Доступ заборонено! Тільки адміністратори можуть змінювати налаштування бота."
        )
    return user


class TextTemplateResponse(BaseModel):
    id: str
    template_key: str
    template_text: str
    description: Optional[str] = None
    last_updated: datetime


class UpdateTemplateRequest(BaseModel):
    template_text: str
    description: Optional[str] = None


@router.get("/text-templates")
async def get_text_templates(
    search: Optional[str] = Query(None),
    admin_user: User = Depends(get_admin_user)
) -> List[TextTemplateResponse]:
    """Get all text templates with optional search filter"""
    try:
        query = {}
        if search:
            # Case-insensitive search in key and description
            query = {
                "$or": [
                    {"template_key": {"$regex": search, "$options": "i"}},
                    {"description": {"$regex": search, "$options": "i"}}
                ]
            }
            
        templates = await TextTemplate.find(query).sort("template_key").to_list()
        
        result = []
        for template in templates:
            result.append(TextTemplateResponse(
                id=str(template.id),
                template_key=template.template_key,
                template_text=template.template_text,
                description=template.description,
                last_updated=template.last_updated
            ))
        
        return result
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/text-templates/{template_id}")
async def get_text_template(
    template_id: str,
    admin_user: User = Depends(get_admin_user)
) -> TextTemplateResponse:
    """Get a specific text template by ID"""
    try:
        template = await TextTemplate.get(template_id)
        if not template:
            raise HTTPException(status_code=404, detail="Шаблон не знайдено")
        
        return TextTemplateResponse(
            id=str(template.id),
            template_key=template.template_key,
            template_text=template.template_text,
            description=template.description,
            last_updated=template.last_updated
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/text-templates/{template_id}")
async def update_text_template(
    template_id: str,
    request: UpdateTemplateRequest,
    admin_user: User = Depends(get_admin_user)
) -> TextTemplateResponse:
    """Update a text template"""
    try:
        template = await TextTemplate.get(template_id)
        if not template:
            raise HTTPException(status_code=404, detail="Шаблон не знайдено")
        
        template.template_text = request.template_text
        if request.description is not None:
            template.description = request.description
        
        template.last_updated = datetime.now()
        await template.save()
        
        # Clear template cache
        import importlib
        try:
            text_templates = importlib.import_module('app.utils.text_templates')
            if hasattr(text_templates, 'clear_template_cache'):
                text_templates.clear_template_cache()
        except ImportError:
            # If the module doesn't exist, we don't need to worry
            pass
        
        return TextTemplateResponse(
            id=str(template.id),
            template_key=template.template_key,
            template_text=template.template_text,
            description=template.description,
            last_updated=template.last_updated
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/clear-template-cache")
async def clear_cache(admin_user: User = Depends(get_admin_user)):
    """Clear the template cache to force reloading from database"""
    try:
        import importlib
        try:
            text_templates = importlib.import_module('app.utils.text_templates')
            if hasattr(text_templates, 'clear_template_cache'):
                text_templates.clear_template_cache()
                return {"message": "Кеш шаблонів очищено успішно"}
            else:
                return {"message": "Функція очищення кешу не знайдена"}
        except ImportError:
            return {"message": "Модуль text_templates не знайдено"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
