# Import necessary libraries
import tkinter as tk
from tkinter import ttk
import threading
from autogen.agentchat.contrib.retrieve_user_proxy_agent import RetrieveUserProxyAgent
from autogen import AssistantAgent, UserProxyAgent, GroupChat, GroupChatManager
import chromadb
import autogen

# Function to update the response field in the GUI
def update_response_field(window, text_widget, text):
    # This function is to be run in the main thread to update the GUI safely
    window.after(0, lambda: text_widget.insert(tk.END, text + "\n"))
    window.after(0, lambda: text_widget.see(tk.END))

# Function to handle the submit button action
def submit_problem(problem, selected_call, window, text_widget):
    # Mapping the possible commands to functions
    calls = {
        "norag_chat": norag_chat,
        "rag_chat": rag_chat,
        "call_rag_chat": call_rag_chat
    }
    
    # Checking if the selected call is valid and executing it
    if selected_call in calls:
        threading.Thread(target=calls[selected_call], args=(problem,)).start()
        update_response_field(window, text_widget, "Call executed, closing window.")
    else:
        update_response_field(window, text_widget, "Selected call is not defined")

# Function to set up the GUI
def setup_gui():
    # Creating the main window
    window = tk.Tk()
    window.title("Problem Submission Interface")
    window.geometry("700x600")

    # Creating the problem input field
    tk.Label(window, text="Problem:").grid(row=0, column=0, sticky='e')
    problem_entry = tk.Entry(window, width=65)
    problem_entry.grid(row=0, column=1, sticky='we')

    # Creating the dropdown for call methods
    tk.Label(window, text="Select Call Method: ").grid(row=1, column=0, sticky='e')
    call_methods = tk.StringVar(window)
    call_methods.set("rag_chat")  # Setting default value
    call_dropdown = ttk.Combobox(window, textvariable=call_methods, width=62)
    call_dropdown['values'] = ("norag_chat", "rag_chat", "call_rag_chat")
    call_dropdown.grid(row=1, column=1, sticky='we')

    # Creating the response field
    response_field = tk.Text(window, height=20, width=80)
    response_field.grid(row=3, column=0, columnspan=3, pady=25, sticky='we')

    # Creating the submit button
    submit_button = tk.Button(window, text="Submit", command=lambda: submit_problem(
        problem_entry.get(), 
        call_methods.get(), 
        window, 
        response_field  # Pass the response_field as an argument here
    ))
    submit_button.grid(row=1, column=2, padx=(10,0), sticky='e')  # Fixed by replacing pack() with grid()

    # Configuring the grid system to allow for responsive resizing
    window.grid_columnconfigure(1, weight=1)

    # Starting the GUI event loop
    window.mainloop()

# Definition of the remaining functions (norag_chat, rag_chat, call_rag_chat, and _reset_agents)
# These will be the same as in your original script

# Starting point of the script
if __name__ == "__main__":
    setup_gui()
