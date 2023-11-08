# Import necessary libraries
import tkinter as tk
from tkinter import ttk
import threading
import logging
import io
from autogen.agentchat.contrib.retrieve_user_proxy_agent import RetrieveUserProxyAgent
from autogen import AssistantAgent, UserProxyAgent, GroupChat, GroupChatManager
from contextlib import redirect_stdout, redirect_stderr
import chromadb
import autogen
# Configure logging to write to a file
logging.basicConfig(filename='agent_output.log', level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s')

# Function to update the response field in the GUI
def update_response_field(window, text_widget, text):
    # This function is to be run in the main thread to update the GUI safely
    window.after(0, lambda: text_widget.insert(tk.END, text + "\n"))
    window.after(0, lambda: text_widget.see(tk.END))

def log_agent_output(text):
    # Logs the output to the file
    logging.info(text)

# Function to handle the submit button action
def submit_problem(problem, selected_call, window, text_widget):
    # Mapping the possible commands to functions
    selected_call = selected_call.strip()
    calls = {
        "norag_chat": norag_chat,
        "rag_chat": rag_chat,
        "call_rag_chat": call_rag_chat
    }
    
    if selected_call in calls:
        # Start the process in a separate thread to prevent GUI from freezing
        thread = threading.Thread(target=calls[selected_call], args=(problem,))
        thread.start()
        # After starting the thread, wait for it to complete
        thread.join()
        # Once the thread has completed, update the GUI with success message
        update_response_field(window, text_widget, "Call executed, check log for details.")
    else:
        update_response_field(window, text_widget, "Selected call is not defined")
        log_agent_output("Selected call is not defined")

config_list = [
    {
        "model": "gpt-4-1106-preview",
        "api_key": "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",
    },
]

llm_config = {
    "timeout": 60,
    "seed": 51,
    "config_list": config_list,
    "temperature": 0,
}

# autogen.ChatCompletion.start_logging()
termination_msg = lambda x: isinstance(x, dict) and "TERMINATE" == str(x.get("content", ""))[-9:].upper()

boss = autogen.UserProxyAgent(
    name="Boss",
    is_termination_msg=termination_msg,
    human_input_mode="TERMINATE",
    system_message="The boss who ask questions and give tasks.",
    code_execution_config=False,  # we don't want to execute code in this case.
)

# Instantiate a RetrieveUserProxyAgent with settings for 'boss assistant' role
boss_aid = RetrieveUserProxyAgent(
    name="Boss_Assistant",  # The name of the agent
    is_termination_msg=termination_msg,  # Function to determine if a message is a termination message
    system_message="Assistant who has extra content retrieval power for solving difficult problems.",
    human_input_mode="TERMINATE",  # Mode for handling human inputs
    max_consecutive_auto_reply=3,  # Maximum number of automatic replies without human intervention
    retrieve_config={  # Configuration for content retrieval
        "task": "code",  # Type of task for content retrieval
        # URL to documentation for reference in content retrieval
        "docs_path": "https://github.com/s76354m/NewAutoHelper/blob/main/main.py",
        "chunk_token_size": 1000,  # Token size for chunks of content
        "model": config_list[0]["model"],  # Language model to use
        "client": chromadb.PersistentClient(path="/tmp/chromadb"),  # Database client for persistent storage
        "collection_name": "groupchat",  # Database collection name
        "get_or_create": True,  # Whether to get or create the collection if not exist
    },
    code_execution_config=False,  # Setting to false to prevent code execution in this case
)

coder = AssistantAgent(
    name="Senior_Python_Engineer",
    is_termination_msg=termination_msg,
    system_message="You are a senior python engineer. Reply `TERMINATE` in the end when everything is done.",
    llm_config=llm_config,
)

pm = autogen.AssistantAgent(
    name="Product_Manager",
    is_termination_msg=termination_msg,
    system_message="You are a product manager. Reply `TERMINATE` in the end when everything is done.",
    llm_config=llm_config,
)

reviewer = autogen.AssistantAgent(
    name="Code_Reviewer",
    is_termination_msg=termination_msg,
    system_message="You are a code reviewer. Reply `TERMINATE` in the end when everything is done.",
    llm_config=llm_config,
)

# PROBLEM = "Provide a python script for creating a User Interface to put the problem statement in for this project."

def _reset_agents():
    boss.reset()
    boss_aid.reset()
    coder.reset()
    pm.reset()
    reviewer.reset()

def norag_chat(problem):
    with io.StringIO() as buf, redirect_stdout(buf), redirect_stderr(buf):
    # Simulate agent's work and print statements
        print(f"Norag chat started with problem: {problem}")
    _reset_agents()
    groupchat = GroupChat(
        agents=[boss, coder, pm, reviewer], messages=[], max_round=12
    )
    manager = GroupChatManager(groupchat=groupchat, llm_config=llm_config)
    boss.initiate_chat(manager, message=problem)
    output = buf.getvalue()
    log_agent_output(output)

def rag_chat(problem):
    with io.StringIO() as buf, redirect_stdout(buf), redirect_stderr(buf):
        print(f"Rag chat started with problem: {problem}")    
    _reset_agents()
    groupchat = GroupChat(
        agents=[boss_aid, coder, pm, reviewer], messages=[], max_round=12
    )
    manager = GroupChatManager(groupchat=groupchat, llm_config=llm_config)
    boss_aid.initiate_chat(manager, problem=problem, n_results=3)
    output = buf.getvalue()
    log_agent_output(output)

def call_rag_chat(problem):
    with io.StringIO() as buf, redirect_stdout(buf), redirect_stderr(buf):
        print(f"Call rag chat started with problem: {problem}")    
    _reset_agents()
    # In this case, we will have multiple user proxy agents and we don't initiate the chat
    # with RAG user proxy agent.
    # In order to use RAG user proxy agent, we need to wrap RAG agents in a function and call
    # it from other agents.
    output = buf.getvalue()
    log_agent_output(output)    
    def retrieve_content(message, n_results=3):
        boss_aid.n_results = n_results  # Set the number of results to be retrieved.
        # Check if we need to update the context.
        update_context_case1, update_context_case2 = boss_aid._check_update_context(message)
        if (update_context_case1 or update_context_case2) and boss_aid.update_context:
            boss_aid.problem = message if not hasattr(boss_aid, "problem") else boss_aid.problem
            _, ret_msg = boss_aid._generate_retrieve_user_reply(message)
        else:
            ret_msg = boss_aid.generate_init_message(message, n_results=n_results)
        return ret_msg if ret_msg else message

    
    boss_aid.human_input_mode = "NEVER" # Disable human input for boss_aid since it only retrieves content.
    
    llm_config = {
        "functions": [
            {
                "name": "retrieve_content",
                "description": "retrieve content for code generation and question answering.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "message": {
                            "type": "string",
                            "description": "Refined message which keeps the original meaning and can be used to retrieve content for code generation and question answering.",
                        }
                    },
                    "required": ["message"],
                },
            },
        ],
        "config_list": config_list,
        "timeout": 60,
        "seed": 51,
    }

    for agent in [coder, pm, reviewer]:
        # update llm_config for assistant agents.
        agent.llm_config.update(llm_config)

    for agent in [boss, coder, pm, reviewer]:
        # register functions for all agents.
        agent.register_function(
            function_map={
                "retrieve_content": retrieve_content,
            }
        )

    # Start chatting with boss as this is the user proxy agent.
    boss.initiate_chat(
        manager,
        message=problem,
    )

    groupchat = autogen.GroupChat(
        agents=[boss, coder, pm, reviewer], messages=[], max_round=12
    )
    manager = autogen.GroupChatManager(groupchat=groupchat, llm_config=llm_config)

# Function to set up the GUI
def setup_gui():
    # Creating the main window
    window = tk.Tk()
    window.title("Problem Submission Interface")
    window.geometry("700x600")
    submit_button.grid(row=1, column=2, padx=(10,0), sticky='e')

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

# At the end of your main.py, you can start the GUI
if __name__ == "__main__":
    setup_gui()
