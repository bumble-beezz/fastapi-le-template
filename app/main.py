import uvicorn
from fastapi import FastAPI, Request, status, Form
from fastapi.responses import RedirectResponse
from starlette.middleware import Middleware
from starlette.middleware.sessions import SessionMiddleware
from app.config import get_settings
from app.dependencies import IsUserLoggedIn, SessionDep, AuthDep
from fastapi.templating import Jinja2Templates
from app.utilities import get_flashed_messages
from jinja2 import Environment, FileSystemLoader
from sqlmodel import select
from app.models import User, Album, Track, Comment, Reaction
from app.utilities import flash, create_access_token
from fastapi.staticfiles import StaticFiles
from typing import Optional

app = FastAPI(middleware=[
    Middleware(SessionMiddleware, secret_key=get_settings().secret_key)
]
)
template_env = Environment(loader = FileSystemLoader("app/templates",), )
template_env.globals['get_flashed_messages'] = get_flashed_messages
templates = Jinja2Templates(env=template_env)
static_files = StaticFiles(directory="app/static")

app.mount("/static", static_files, name="static")


@app.get('/', response_class=RedirectResponse)
async def index_view(
  request: Request,
  user_logged_in: IsUserLoggedIn,
):
  if user_logged_in:
    return RedirectResponse(url=request.url_for('home_view'), status_code=status.HTTP_303_SEE_OTHER)
  return RedirectResponse(url=request.url_for('login_view'), status_code=status.HTTP_303_SEE_OTHER)

@app.get("/login")
async def login_view(
  user_logged_in: IsUserLoggedIn,
  request: Request,
):
  if user_logged_in:
    return RedirectResponse(url=request.url_for('home_view'), status_code=status.HTTP_303_SEE_OTHER)
  return templates.TemplateResponse(
          request=request, 
          name="login.html",
      )

@app.post('/login')
def login_action(
  request: Request,
  db: SessionDep,
  username: str = Form(),
  password: str = Form(),
):
  
  user = db.exec(select(User).where(User.username == username)).one_or_none()
  if user and user.check_password(password):
    response = RedirectResponse(url=request.url_for("index_view"), status_code=status.HTTP_303_SEE_OTHER)
    access_token = create_access_token(data={"sub": f"{user.id}"})
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=False,
        samesite="lax",
        secure=True,
    )    
    return response
  else:
    flash(request, 'Invalid username or password')
    return RedirectResponse(url=request.url_for('login_view'), status_code=status.HTTP_303_SEE_OTHER)


@app.get('/logout')
async def logout(request: Request):
    response = RedirectResponse(url=request.url_for("login_view"), status_code=status.HTTP_303_SEE_OTHER)
    response.delete_cookie(key="access_token", httponly=True, samesite="none", secure=True)
    flash(request, 'logged out')
    return response

@app.get('/app')
def home_view(
    request: Request,
    user: AuthDep,
    db: SessionDep,
    album_id: Optional[int] = None,
    track_id: Optional[int] = None,
):
    albums = db.exec(select(Album)).all()

    selected_album = None
    tracks = []
    comment_counts = {} 
    selected_track = None
    comments = []
    likes_count = 0
    dislikes_count = 0

    if album_id:
        selected_album = db.get(Album, album_id)
        if selected_album:
            tracks = db.exec(select(Track).where(Track.album_id == album_id)).all()
            for track in tracks:
                track_comments = db.exec(select(Comment).where(Comment.track_id == track.id)).all()
                comment_counts[track.id] = len(track_comments)

    if track_id:
        selected_track = db.get(Track, track_id)
        if selected_track:
            comments = db.exec(select(Comment).where(Comment.track_id == track_id)).all()
            for comment in comments:
                comment.user = db.get(User, comment.user_id)   # preload user while session is open

            likes_list = db.exec(select(Reaction).where(Reaction.track_id == track_id, Reaction.reaction_type == "like")).all()
            dislikes_list = db.exec(select(Reaction).where(Reaction.track_id == track_id, Reaction.reaction_type == "dislike")).all()
            likes_count = len(likes_list)
            dislikes_count = len(dislikes_list)

    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "albums": albums,
            "selected_album": selected_album,
            "tracks": tracks,
            "comment_counts": comment_counts,
            "selected_track": selected_track,
            "comments": comments,
            "likes_count": likes_count,
            "dislikes_count": dislikes_count,
            "user": user,
        },
    )


@app.post('/add_comment')
def add_comment_action(
    request: Request,
    db: SessionDep,
    user: AuthDep,
    track_id: int = Form(),
    text: str = Form(),
    album_id: int = Form(),
):
    comment = Comment(text=text, track_id=track_id, user_id=user.id)
    db.add(comment)
    db.commit()
    return RedirectResponse(url=f"/app?album_id={album_id}&track_id={track_id}", status_code=status.HTTP_303_SEE_OTHER)


@app.post('/delete_comment')
def delete_comment_action(
    request: Request,
    db: SessionDep,
    user: AuthDep,
    comment_id: int = Form(),
    album_id: int = Form(),
    track_id: int = Form(),
):
    comment = db.get(Comment, comment_id)
    if comment and comment.user_id == user.id:
        db.delete(comment)
        db.commit()
    return RedirectResponse(url=f"/app?album_id={album_id}&track_id={track_id}", status_code=status.HTTP_303_SEE_OTHER)


@app.post('/react')
def react_action(
    request: Request,
    db: SessionDep,
    user: AuthDep,
    track_id: int = Form(),
    reaction_type: str = Form(),
    album_id: int = Form(),
):
    if reaction_type not in ["like", "dislike"]:
        return RedirectResponse(url=f"/app?album_id={album_id}&track_id={track_id}", status_code=status.HTTP_303_SEE_OTHER)

    existing = db.exec(select(Reaction).where(Reaction.track_id == track_id, Reaction.user_id == user.id)).one_or_none()
    if existing:
        db.delete(existing)
        db.commit()

    new_reaction = Reaction(track_id=track_id, user_id=user.id, reaction_type=reaction_type)
    db.add(new_reaction)
    db.commit()

    return RedirectResponse(url=f"/app?album_id={album_id}&track_id={track_id}", status_code=status.HTTP_303_SEE_OTHER)