#!/usr/bin/env python3
"""
Test script for Personal Desktop AI Assistant
This script demonstrates the assistant's functionality with text input instead of voice
"""

import datetime
import webbrowser
import os
import subprocess
import requests

# Function to get current time
def get_time():
    current_time = datetime.datetime.now().strftime("%I:%M %p")
    return f"The current time is {current_time}"

# Function to get current date
def get_date():
    current_date = datetime.datetime.now().strftime("%B %d, %Y")
    return f"Today's date is {current_date}"

# Function to get weather information
def get_weather(city="Hyderabad"):
    # Note: Replace with your actual API key for weather functionality
    api_key = "YOUR_OPENWEATHERMAP_API_KEY"
    base_url = "http://api.openweathermap.org/data/2.5/weather?"

    if api_key == "YOUR_OPENWEATHERMAP_API_KEY":
        return "Weather functionality requires an OpenWeatherMap API key. Please get one from https://openweathermap.org/api and update the api_key variable."

    complete_url = base_url + "appid=" + api_key + "&q=" + city + "&units=metric"

    try:
        response = requests.get(complete_url)
        data = response.json()

        if data["cod"] != "404":
            main_data = data["main"]
            weather_data = data["weather"][0]
            temperature = main_data["temp"]
            humidity = main_data["humidity"]
            description = weather_data["description"]

            weather_info = f"The temperature in {city} is {temperature}°C with {description}. Humidity is {humidity}%."
            return weather_info
        else:
            return "City not found."
    except:
        return "Unable to fetch weather information. Please check your internet connection."

# Function to open applications
def open_application(app_name):
    app_commands = {
        "chrome": "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
        "firefox": "C:\\Program Files\\Mozilla Firefox\\firefox.exe",
        "notepad": "notepad.exe",
        "calculator": "calc.exe",
        "word": "C:\\Program Files\\Microsoft Office\\root\\Office16\\WINWORD.EXE",
        "excel": "C:\\Program Files\\Microsoft Office\\root\\Office16\\EXCEL.EXE",
        "powerpoint": "C:\\Program Files\\Microsoft Office\\root\\Office16\\POWERPNT.EXE"
    }

    if app_name in app_commands:
        try:
            subprocess.Popen(app_commands[app_name])
            return f"Opening {app_name}"
        except:
            return f"Sorry, I couldn't open {app_name}"
    else:
        return f"I don't know how to open {app_name}"

# Function to search the internet
def search_internet(query):
    url = f"https://www.google.com/search?q={query}"
    webbrowser.open(url)
    return f"Searching for {query}"

# Function to play music
def play_music():
    music_dir = "C:\\Users\\G RUSHINDHRA\\Music"  # Change this to your music directory
    try:
        if os.path.exists(music_dir):
            songs = os.listdir(music_dir)
            if songs:
                os.startfile(os.path.join(music_dir, songs[0]))
                return "Playing music"
            else:
                return "No music files found in your music directory"
        else:
            return f"Music directory not found: {music_dir}"
    except:
        return "Unable to play music. Please check your music directory."

# Function to stop music (basic implementation)
def stop_music():
    try:
        os.system("taskkill /f /im wmplayer.exe")  # For Windows Media Player
        os.system("taskkill /f /im vlc.exe")  # For VLC
        return "Stopping music"
    except:
        return "Unable to stop music"

# Main function to process commands
def process_command(command):
    command = command.lower()

    if "time" in command:
        response = get_time()
    elif "date" in command:
        response = get_date()
    elif "weather" in command:
        response = get_weather()
    elif "open" in command:
        if "chrome" in command or "browser" in command:
            response = open_application("chrome")
        elif "firefox" in command:
            response = open_application("firefox")
        elif "notepad" in command or "editor" in command:
            response = open_application("notepad")
        elif "calculator" in command or "calc" in command:
            response = open_application("calculator")
        elif "word" in command:
            response = open_application("word")
        elif "excel" in command:
            response = open_application("excel")
        elif "powerpoint" in command:
            response = open_application("powerpoint")
        else:
            response = "I don't know how to open that application"
    elif "search" in command:
        query = command.replace("search", "").strip()
        response = search_internet(query)
    elif "play music" in command or "play song" in command:
        response = play_music()
    elif "stop music" in command:
        response = stop_music()
    elif "hello" in command or "hi" in command:
        response = "Hello! How can I help you today?"
    elif "bye" in command or "goodbye" in command or "quit" in command or "exit" in command:
        response = "Goodbye! Have a great day!"
        return response, True  # True indicates to exit
    elif "thank you" in command or "thanks" in command:
        response = "You're welcome!"
    else:
        response = "I'm sorry, I didn't understand that command. Please try again."

    return response, False

def main():
    print("Personal Desktop AI Assistant - Text Mode")
    print("=========================================")
    print("Type your commands below. Type 'quit' to exit.")
    print()

    while True:
        command = input("You: ").strip()
        if command.lower() in ['quit', 'exit', 'bye', 'goodbye']:
            print("Assistant: Goodbye! Have a great day!")
            break

        if command:
            response, should_exit = process_command(command)
            print(f"Assistant: {response}")
            if should_exit:
                break
        else:
            print("Assistant: Please enter a command.")

if __name__ == "__main__":
    main()