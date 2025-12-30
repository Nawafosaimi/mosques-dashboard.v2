"""Script to generate hashed passwords for auth_config.yaml"""
import streamlit_authenticator as stauth

# Generate hashed passwords - new API in 0.4.x
passwords = ["admin123", "nawaf123", "user123", "user123"]
hashed_passwords = stauth.Hasher(passwords).hash_passwords()

print("Hashed passwords for auth_config.yaml:\n")
usernames = ["admin", "nawaf", "user1", "user2"]
for username, hashed in zip(usernames, hashed_passwords):
    print(f"{username}: {hashed}")
