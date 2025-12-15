from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from datetime import timedelta
from . import crud, models, schemas, auth
from .database import engine, get_db

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Task Manager API", description="A simple task manager with authentication", version="1.0.0")

# تنظیمات CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/register/", response_model=schemas.UserResponse)
def register(user: schemas.UserCreate, db: Session = Depends(get_db)):
    db_user = crud.get_user_by_email(db, email=user.email)
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    db_user = crud.get_user_by_username(db, username=user.username)
    if db_user:
        raise HTTPException(status_code=400, detail="Username already taken")
    return crud.create_user(db=db, user=user)

@app.post("/token", response_model=schemas.Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = auth.authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=auth.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth.create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/users/me/", response_model=schemas.UserResponse)
async def read_users_me(current_user: schemas.UserResponse = Depends(auth.get_current_active_user)):
    return current_user

@app.post("/tasks/", response_model=schemas.TaskResponse)
def create_task(
    task: schemas.TaskCreate,
    current_user: schemas.UserResponse = Depends(auth.get_current_active_user),
    db: Session = Depends(get_db)
):
    return crud.create_task(db=db, task=task, user_id=current_user.id)

@app.get("/tasks/", response_model=list[schemas.TaskResponse])
def read_tasks(
    skip: int = 0,
    limit: int = 100,
    completed: bool = None,
    category: str = None,
    current_user: schemas.UserResponse = Depends(auth.get_current_active_user),
    db: Session = Depends(get_db)
):
    tasks = crud.get_tasks(db, user_id=current_user.id, skip=skip, limit=limit, completed=completed, category=category)
    return tasks

@app.get("/tasks/{task_id}", response_model=schemas.TaskResponse)
def read_task(
    task_id: int,
    current_user: schemas.UserResponse = Depends(auth.get_current_active_user),
    db: Session = Depends(get_db)
):
    db_task = crud.get_task(db, task_id=task_id, user_id=current_user.id)
    if db_task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return db_task

@app.put("/tasks/{task_id}", response_model=schemas.TaskResponse)
def update_task(
    task_id: int,
    task_update: schemas.TaskUpdate,
    current_user: schemas.UserResponse = Depends(auth.get_current_active_user),
    db: Session = Depends(get_db)
):
    db_task = crud.update_task(db, task_id=task_id, task_update=task_update, user_id=current_user.id)
    if db_task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return db_task

@app.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(
    task_id: int,
    current_user: schemas.UserResponse = Depends(auth.get_current_active_user),
    db: Session = Depends(get_db)
):
    success = crud.delete_task(db, task_id=task_id, user_id=current_user.id)
    if not success:
        raise HTTPException(status_code=404, detail="Task not found")
    return

# برای استفاده از OAuth2PasswordRequestForm باید import شود
from fastapi.security import OAuth2PasswordRequestForm
