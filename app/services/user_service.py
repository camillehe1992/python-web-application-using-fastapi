from datetime import timedelta

from fastapi import HTTPException, status
from pydantic import UUID4
from sqlalchemy.orm import Session

from core.security import get_password_hash, pwd_context, create_access_token
from config.settings import settings
from repositories.user_repository import UserRepository
from schemas.user import UserIn, UserLogin, UserInDBBase
from core.password_validator import validate_password
from core.email_validator import validate_email


class UserService:
    """
    Service class for handling user-related operations.
    """

    def __init__(self, session: Session):
        """
        Initialize the service.

        Args:
            session (Session): Database session.
        """
        self.repository = UserRepository(session)

    def create(self, data: UserIn) -> UserInDBBase:
        """
        Create a new user.

        Args:
            data (UserIn): User data.

        Returns:
            UserInDBBase: Created user data.
        """
        if self.repository.user_exists_by_email(data.email):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Email {data.email} already registered",
            )
        if self.repository.user_exists_by_username(data.username):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Username {data.username} already registered",
            )

        validate_password(data.password)
        validate_email(data.email)

        hashed_password = get_password_hash(data.password)
        return self.repository.create(data, hashed_password)

    def login(self, data: UserLogin):
        """
        User login.

        Args:
            data (UserLogin): Login data with username and password.

        Returns:
            dict: Token response.
        """
        user = self.repository.get_user_by_username(data.username)
        if not user or not pwd_context.verify(data.password, user.hashed_password):
            raise HTTPException(
                status_code=401,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user.username}, expires_delta=access_token_expires
        )
        return {"access_token": access_token, "token_type": "bearer"}

    def is_superuser(self, _id: UUID4) -> bool:
        """
        Check if the user is a superuser.

        Args:
            _id (UUID4): User ID.

        Returns:
            bool: True if the user is a superuser, False otherwise.
        """
        if not self.repository.user_exists_by_id(_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=f"User {_id} not found"
            )

        user = self.repository.get_user_object_by_id(_id)
        return user.is_superuser

    def delete_user(self, _id: UUID4) -> bool:
        """
        Delete a user.

        Args:
            _id (UUID4): User ID.

        Returns:
            bool: True if the user is successfully deleted, False otherwise.
        """
        if not self.repository.user_exists_by_id(_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=f"User {_id} not found"
            )

        user = self.repository.get_user_object_by_id(_id)
        self.repository.delete_user(user)
        return True
