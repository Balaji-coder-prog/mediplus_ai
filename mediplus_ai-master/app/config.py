import os

class Config:
    SECRET_KEY = 'mediplus_secret_key_2026'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///mediplus.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False