# Import necessary libraries and functions
from autogen.agentchat.contrib.retrieve_user_proxy_agent import RetrieveUserProxyAgent
from autogen import AssistantAgent, UserProxyAgent, GroupChat, GroupChatManager
import chromadb
import autogen
import tkinter as tk
from tkinter import ttk
import threading

# Define the on_submit function for GUI interactions
def submit_problem(problem, selected_call, window):
    # Directly call the functions without importing from main.py as we are already in the main script
    calls = {
        "norag_chat": norag_chat,
        "rag_chat": rag_chat,
        "call_rag_chat": call_rag_chat
    }
        # Execute the selected call with the problem as argument
    if selected_call in calls:
        # Start the process in a separate thread to prevent GUI from freezing
        threading.Thread(target=calls[selected_call], args=(problem,)).start()
        window.destroy()  # This will close the GUI window
    else:
        print("Selected call is not defined")

# Define the GUI setup function
def setup_gui():
    window = tk.Tk()
    window.title("Problem Submission Interface")

    # Text field for the problem
    tk.Label(window, text="Problem:").grid(row=0, column=0)
    problem_entry = tk.Entry(window, width=50)
    problem_entry.grid(row=0, column=1)

    # Dropdown menu for selecting the call
    tk.Label(window, text="Select Call:").grid(row=1, column=0)
    call_methods = tk.StringVar(window)
    call_methods.set("norag_chat")  # default value
    call_dropdown = ttk.Combobox(window, textvariable=call_methods)
    call_dropdown['values'] = ("norag_chat", "rag_chat", "call_rag_chat")
    call_dropdown.grid(row=1, column=1)

    # Submit button
    submit_button = tk.Button(window, text="Submit", command=lambda: submit_problem(problem_entry.get(), call_methods.get(), window))
    submit_button.grid(row=2, column=0, columnspan=2)

    # Start the GUI event loop
    window.mainloop()

config_list = [
    {
        "model": "gpt-4",
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
        "docs_path": "https://docs.python.org/3/reference/index.html",
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
    _reset_agents()
    groupchat = GroupChat(
        agents=[boss, coder, pm, reviewer], messages=[], max_round=12
    )
    manager = GroupChatManager(groupchat=groupchat, llm_config=llm_config)
    boss.initiate_chat(manager, message=problem)

def rag_chat(problem):
    _reset_agents()
    groupchat = GroupChat(
        agents=[boss_aid, coder, pm, reviewer], messages=[], max_round=12
    )
    manager = GroupChatManager(groupchat=groupchat, llm_config=llm_config)
    boss_aid.initiate_chat(manager, problem=problem, n_results=3)

def call_rag_chat(problem):
    _reset_agents()
    # In this case, we will have multiple user proxy agents and we don't initiate the chat
    # with RAG user proxy agent.
    # In order to use RAG user proxy agent, we need to wrap RAG agents in a function and call
    # it from other agents.
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

    groupchat = autogen.GroupChat(
        agents=[boss, coder, pm, reviewer], messages=[], max_round=12
    )
    manager = autogen.GroupChatManager(groupchat=groupchat, llm_config=llm_config)

    # Start chatting with boss as this is the user proxy agent.
    boss.initiate_chat(
        manager,
        message=problem,
    )

# At the end of your main.py, you can start the GUI
if __name__ == "__main__":
    setup_gui()
