from fastapi import APIRouter,Depends,Request, HTTPException

router= APIRouter(
    prefix="api/auth"
)