import typer
from app.database import create_db_and_tables, get_cli_session, drop_all
from app.models import *
from fastapi import Depends
from sqlmodel import select
from sqlalchemy.exc import IntegrityError
from app.utilities import encrypt_password

cli = typer.Typer()

@cli.command()
def initialize():
    with get_cli_session() as db:
        drop_all() 
        create_db_and_tables() 
        
        bob = UserBase(username='bob', email='bob@mail.com', password=encrypt_password("bobpass"))
        bob_db = User.model_validate(bob)

        db.add(bob_db)
        db.commit()    
        db.refresh(bob_db)   

        #two users so i can make sure bob can't delete wendy's comments
        wendy = UserBase(username='wendy', email='wendy@mail.com', password=encrypt_password("wendypass"))
        wendy_db = User.model_validate(wendy)
        db.add(wendy_db)
        db.commit()    
        db.refresh(wendy_db) 

        album_data = [
            {"title": "Tung Tung Sahur", "artist": "DJ Stupid", "image_url": "https://weblabs.web.app/api/brainrot/1.webp"},
            {"title": "Bombardiro Crocodilo", "artist": "DJ Idle", "image_url": "https://weblabs.web.app/api/brainrot/2.webp"},
            {"title": "Bombombini Gusini", "artist": "DJ Find a Job", "image_url": "https://weblabs.web.app/api/brainrot/3.webp"},
            {"title": "Brr Brr Patapim", "artist": "DJ Brainless", "image_url": "https://weblabs.web.app/api/brainrot/4.webp"},
            {"title": "Chimpanzini Bananini", "artist": "DJ Nothing Up There", "image_url": "https://weblabs.web.app/api/brainrot/5.webp"},
        ]

        albums = []
        for data in album_data:
            album = Album(**data)
            db.add(album)
            db.commit()
            db.refresh(album)
            albums.append(album)

        wendy_comments = [
            "im bored let's stop making music",
            "bad.",
            "not good.",
            "this is stupid",
            "please stop",
            "absolute trash",
            "who approved this",
            "my ears are bleeding",
            "make it stop",
            "never again"
        ]
        comment_index = 0

        for album in albums:
            for i in range(1, 4):
                track = Track(title=f"Track {i}", album_id=album.id)
                db.add(track)
                db.commit()
                db.refresh(track)

                comment_wendy = Comment(
                    text=wendy_comments[comment_index % len(wendy_comments)],
                    track_id=track.id,
                    user_id=wendy_db.id,
                    )
                db.add(comment_wendy)
                db.commit()
                comment_index = comment_index + 1

                #i wanted some tracks to have more than one comment
                if i % 2 == 0: 
                    comment_wendy2 = Comment(
                        text=wendy_comments[comment_index % len(wendy_comments)],
                        track_id=track.id,
                        user_id=wendy_db.id,
                    )
                    db.add(comment_wendy2)
                    db.commit()
                    comment_index += 1

                reaction = Reaction(reaction_type = "dislike",track_id = track.id,user_id=wendy_db.id,)
                db.add(reaction)
                db.commit()

        print("Database Initialized")

@cli.command()
def test():
    print("You're already in the test")


if __name__ == "__main__":
    cli()