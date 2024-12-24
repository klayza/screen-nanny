## What will this program do?

An AI will monitor what you are looking at will tell you if you are getting distracted.

> tip: before you turn your pc on, think of why you should. if you can't think of a good reason, don't turn it on.

## Example

You are working on a project and need to do some research. While doing research you see something unrelated but interesting so you click on it. An hour passes by and you realize you wasted your time. Next time with the program enabled an ai 'nanny' will watch what you are looking at and keep you on track.

## Requirements

Modes:
- Default: Checks if the current screen is a general time wasting app.
- Focus: Start a focus session by giving the ai a description of what you are doing.

Functions:
- Display modal: Must display full screen messages that capture the user's attention.
- Text entry: Will allow the user to enter a description of their goal to enable a focus session. Shown on the display modal.
- Hotey for starting focus session: When a certain hotkey is pushed it will open the focus dialog.
- Memory: Allow the ai to keep track of the user screen history up to a time. The default will be an hour. 
- Screen capture: A picture of the entire screen will be taken every 60 seconds (default value) 
- Grab system info: Gets information such as active window, active browser tab, and for duration (if possible)
- AI: Use a standard vision modal to interpret the current screen + system info + memory and return an action.
- AI actions: The AI will use function calling to do the following: showMessage(message) which will open a dialog with x message
- Logging: All pictures taken and their descriptions, system info with their timestamp


