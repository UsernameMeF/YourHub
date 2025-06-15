# **Social Network Project**

Welcome to the Social Network Project – a full-featured social network developed with Django. The project includes systems for friends and subscriptions, private chats, user authentication, communities, main page publications with sorting and various display types, as well as reactions like likes, dislikes, and reposts.

## **🚀 Getting Started**

Follow these instructions to get your project up and running on your local machine for development and testing.

### **📋 Prerequisites**

Ensure you have the following software installed:

* **Python 3.10+**  
* **pip** (Python package installer)  
* **Git** (for cloning the repository)  
* **Redis** (in-memory data store used for Channels)

### **💻 Installation**

#### **Clone the repository:**

git clone https://github.com/UsernameMeF/YourHub.git

*(Assumes the repository will be located at this link. If not, please replace it with the correct one.)*

#### **Create and activate a virtual environment:**

This isolates your project dependencies from your global Python installation.

**Create the virtual environment:**

python3 \-m venv venv

*(Or python \-m venv venv if you only have python)*

**Activate the virtual environment:**

* **For Linux/macOS:**  
  source venv/bin/activate

* **For Windows (Command Prompt):**  
  venv\\Scripts\\activate.bat

* **For Windows (PowerShell):**  
  venv\\Scripts\\Activate.ps1

You'll see (venv) at the beginning of your command line, indicating the virtual environment is active.

#### **Configure environment variables:**

Copy the .env.example file to .env and fill it with the necessary values. This step is crucial as Django reads sensitive data from .env.

* **For Linux/macOS:**  
  cp .env.example .env

* **For Windows:**  
  copy .env.example .env

Open the created .env file in a text editor (e.g., VS Code, Sublime Text) and provide your data.

**Example .env content (may vary based on your settings.py):**

SECRET\_KEY='django-insecure-your-secret-key-here' \# Generate a new and complex one for production\!  

**Important:** For SECRET\_KEY in production, generate a unique, long, and complex key\!

#### **Install project dependencies:**

All required libraries are listed in the requirements.txt file.

pip install \-r requirements.txt

#### **Set up the database:**

Run Django migrations to create the database schema.

python your\_hub/manage.py makemigrations
python your\_hub/manage.py migrate

#### **Create a superuser (optional):**

This will allow you to access the Django administration panel.

python your\_hub/manage.py createsuperuser

Follow the prompts in the command line to create a username and password.

## **🚀 Running the Project**

The project uses Django Channels for WebSocket functionality (e.g., for chat). Therefore, for its full functionality, you need to run both the Django server and the Channels server (Daphne) with Redis.

### **1\. Start the Redis Server**

Ensure your Redis server is running and accessible. The method for starting Redis depends on your operating system and how Redis was installed.

* **Example for Linux/macOS (if Redis is installed as a service):**  
  sudo service redis-server start

* Example for Windows (if Redis Desktop Manager is installed or via MSI installer):  
  Start Redis via the shortcut in the "Start Menu" or by executing redis-server.exe from the Redis installation folder.

### **2\. Start the Django Server (HTTP)**

Open your first terminal, activate the virtual environment (if not already active), and start the standard Django development server:

python your\_hub/manage.py runserver

The server will be available at: [http://127.0.0.1:8000/](http://127.0.0.1:8000/)

### **3\. Start the Channels Server (Daphne)**

Open your second terminal, activate the virtual environment (if not already active), and start the Daphne server, which will handle WebSockets:

daphne your\_hub.asgi:application \-p 8001

The Daphne server will listen for WebSockets on port 8001\.

## **👨‍💻 Developer**

**UsernameMeF** \- [GitHub Profile](https://github.com/UsernameMeF)