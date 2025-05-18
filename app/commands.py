import click
from flask import current_app
from flask.cli import with_appcontext
from werkzeug.security import generate_password_hash
from .models.models import User, db
from datetime import datetime, timedelta
import uuid

@click.command('create-user')
@click.argument('email')
@click.argument('password')
@click.option('--admin', is_flag=True, help='Make this user an admin')
def create_user(email, password, admin):
    """Create a new user with the given email and password.
    
    Args:
        email: Email address for the user
        password: Password for the user
        admin: Whether the user should have admin privileges
    """
    # Check if a user with this email already exists
    existing_user = User.query.filter_by(email=email).first()
    if existing_user:
        click.echo(f"User with email {email} already exists.")
        return
    
    # Create a new user
    user = User(
        spotify_id=f"local_{uuid.uuid4().hex[:20]}",  # Generate a unique spotify_id
        email=email,
        display_name=f"User {email.split('@')[0]}",
        access_token=generate_password_hash(f"{email}:{password}", method='pbkdf2:sha256'),
        refresh_token=generate_password_hash(f"{password}:{email}", method='pbkdf2:sha256'),
        token_expiry=datetime.utcnow() + timedelta(days=365),  # Set far in the future
        is_admin=admin
    )
    
    db.session.add(user)
    try:
        db.session.commit()
        user_type = "Admin" if admin else "User"
        click.echo(f"{user_type} {email} created successfully with spotify_id: {user.spotify_id}")
        click.echo("Note: This is a local user account. To log in, you'll need to implement local authentication.")
    except Exception as e:
        db.session.rollback()
        click.echo(f"Error creating user: {str(e)}")
        raise

def init_app(app):
    """Register CLI commands with the application."""
    app.cli.add_command(create_user)
