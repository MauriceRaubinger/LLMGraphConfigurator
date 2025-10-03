import sys
import os
import json
from typing import Dict, Any, List
from langchain.chat_models import init_chat_model
from langchain_community.vectorstores import FAISS
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from langchain_core.messages import HumanMessage
from langchain_google_genai import GoogleGenerativeAIEmbeddings

# --- Environment Configuration ---
os.environ["LANGSMITH_TRACING"] = "true"
os.environ["LANGSMITH_API_KEY"] = "key"
os.environ["GOOGLE_API_KEY"] = "key"

# --- LLM and Embeddings Initialization ---
llm = init_chat_model("gemini-2.0-flash-lite", model_provider="google_genai")
embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")

# --- File and Index Paths ---
script_dir = os.path.dirname(os.path.abspath(__file__))
file_path = os.path.join(script_dir, "Documentation.txt")
index_dir = os.path.join(script_dir, "faiss_Documentation")

# --- Load or Build FAISS Index ---
if os.path.exists(index_dir):
    vector_store = FAISS.load_local(index_dir, embeddings, allow_dangerous_deserialization=True)
else:
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            text = f.read()
    except FileNotFoundError:
        sys.exit(1)

    docs = [Document(page_content=text)]
    splitter = RecursiveCharacterTextSplitter(chunk_size=400, chunk_overlap=100, add_start_index=True)
    chunks = splitter.split_documents(docs)
    vector_store = FAISS.from_documents(chunks, embeddings)
    vector_store.save_local(index_dir)

# --- Graph Data Structures ---
class Node:
    def __init__(self, node_id: int, node_type: str, content=None):
        self.id = node_id
        self.type = node_type
        self.content = content or []

class Connection:
    def __init__(self, from_node: Node, to_node: Node, output_type="output"):
        self.from_node = from_node
        self.to_node = to_node
        self.output_type = output_type

class Graph:
    def __init__(self):
        self.nodes = []
        self.connections = []
        self.next_node_id = 1

    def get_node_by_id(self, node_id: int) -> Node:
        return next((n for n in self.nodes if n.id == node_id), None)

    def get_inp_node(self):
        for n in self.nodes:
            if n.type == 'input':
                return n
        return None

    def get_incoming_edge_nodes(self, node: Node):
        return [c.from_node for c in self.connections if c.to_node == node]

    def get_outgoing_edge_nodes(self, node: Node):
        return [c.to_node for c in self.connections if c.from_node == node]

    def add_node(self, node_type: str, content=None) -> Node:
        node = Node(self.next_node_id, node_type, content)
        self.nodes.append(node)
        self.next_node_id += 1
        return node

    def add_connection(self, from_node: Node, to_node: Node, output_type="output"):
        for connection in self.connections:
            if (connection.from_node == from_node and
                    connection.to_node == to_node and
                    connection.output_type == output_type):
                return
        new_connection = Connection(from_node, to_node, output_type)
        self.connections.append(new_connection)

    def remove_node(self, node: Node):
        self.connections = [c for c in self.connections if c.from_node != node and c.to_node != node]
        self.nodes.remove(node)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "nodes": [{"id": n.id, "type": n.type, "content": n.content} for n in self.nodes],
            "connections": [{"from": c.from_node.id, "to": c.to_node.id, "output_type": c.output_type} for c in self.connections]
        }

    def from_dict(self, graph_dict):
        self.nodes = []
        self.connections = []
        node_id_map = {}
        for node_data in graph_dict["nodes"]:
            node = Node(node_data["id"], node_data["type"])
            node.content = node_data.get("content", [])
            self.nodes.append(node)
            node_id_map[node_data["id"]] = node
            if node.id >= self.next_node_id:
                self.next_node_id = node.id + 1
        for conn_data in graph_dict["connections"]:
            from_node = node_id_map[conn_data["from"]]
            to_node = node_id_map[conn_data["to"]]
            output_type = conn_data.get("output_type", "output")
            self.add_connection(from_node, to_node, output_type)

    def topological_sort(self) -> List[int]:
        indegree = {n.id: 0 for n in self.nodes}
        for c in self.connections:
            indegree[c.to_node.id] += 1
        queue = [n.id for n in self.nodes if indegree[n.id] == 0]
        order = []
        while queue:
            nid = queue.pop(0)
            order.append(nid)
            for c in self.connections:
                if c.from_node.id == nid:
                    indegree[c.to_node.id] -= 1
                    if indegree[c.to_node.id] == 0:
                        queue.append(c.to_node.id)
        if len(order) != len(self.nodes):
            raise ValueError("Cycle detected in the graph; cannot proceed.")
        return order

# --- DAG-Based RAG Workflow ---
class LLMWorkflow:
    def __init__(self, graph: Graph, vector_store: FAISS, llm):
        self.graph = graph
        self.vector_store = vector_store
        self.llm = llm
        self.node_funcs: Dict[int, Any] = {}
        self.exec_order: List[int] = []

    def get_graph(self, path: str):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            self.graph.from_dict(data)
            print("Graph loaded:")
            print(json.dumps(self.graph.to_dict(), indent=2))
        except FileNotFoundError:
            print(f"No saved graph at {path}")

    def clear_memory(self):
        memory_nodes = [node for node in self.graph.nodes if node.type == 'memory']
        for memory_node in memory_nodes:
            file_path = os.path.join(script_dir, f"memory_{memory_node.id}.txt")
            with open(file_path, 'w', encoding='utf-8') as f:
                pass  # Clear the file

    def build(self):
        start_node = self.graph.get_inp_node()
        reachable = [start_node]

        def reachable_nodes(node: Node):
            if node not in reachable:
                reachable.append(node)
            out = self.graph.get_outgoing_edge_nodes(node)
            for n in out:
                reachable_nodes(n)

        reachable_nodes(start_node)
        for n in self.graph.nodes[:]:
            if n not in reachable:
                self.graph.remove_node(n)

        # Factories for each node type
        def input_factory(node: Node):
            def fn(state: Dict[str, Any]) -> Dict[str, Any]:
                print(f"[Node {node.id} - INPUT] question='{state['question']}'")
                state["activation"][str(node.id)] = True
                state['data'][str(node.id)] = state['question']
                memory_targets = [c.to_node.id for c in self.graph.connections if c.from_node == node and c.to_node.type == 'memory']
                for memory_node_id in memory_targets:
                    file_path = os.path.join(script_dir, f"memory_{memory_node_id}.txt")
                    try:
                        with open(file_path, 'a', encoding='utf-8') as f:
                            f.write(str(state['data'][str(node.id)]) + "\n\n")
                    except (PermissionError, OSError) as e:
                        print(f"Error writing to {file_path}: {e}")
                return state
            return fn

        def retrieval_factory(node: Node):
            def fn(state: Dict[str, Any]) -> Dict[str, Any]:
                incoming = self.graph.get_incoming_edge_nodes(node)
                flag = True
                for i in incoming:
                    if i.type != "condition":
                        if str(i.id) in state['activation'].keys() and not state['activation'][str(i.id)]:
                            flag = False
                        elif str(i.id) not in state['activation'].keys():
                            flag = False
                if flag:
                    texts = [state['data'][str(i.id)] for i in incoming if i.type != "condition"]
                    print(f"[Node {node.id} - RETRIEVAL] inputs={texts}")
                    inp = "".join(texts)
                    docs = self.vector_store.similarity_search(inp, k=4)
                    print(f"[Node {node.id}] retrieved: " + "\n\n".join(doc.page_content for doc in docs))
                    state["data"][str(node.id)] = "\n\n".join(doc.page_content for doc in docs)
                    state["activation"][str(node.id)] = True
                    memory_targets = [c.to_node.id for c in self.graph.connections if c.from_node == node and c.to_node.type == 'memory']
                    for memory_node_id in memory_targets:
                        file_path = os.path.join(script_dir, f"memory_{memory_node_id}.txt")
                        try:
                            with open(file_path, 'a', encoding='utf-8') as f:
                                f.write(str(state['data'][str(node.id)]) + "\n\n")
                        except (PermissionError, OSError) as e:
                            print(f"Error writing to {file_path}: {e}")
                return state
            return fn

        def condition_factory(node: Node):
            def fn(state: Dict[str, Any]) -> Dict[str, Any]:
                incoming = self.graph.get_incoming_edge_nodes(node)
                texts = [state['data'][str(i.id)] for i in incoming if str(i.id) in state['data']]
                if len(node.content) == 0:
                    raise ValueError(f"Condition node empty")
                if node.content[0] in ''.join(texts):
                    state['data'][str(node.id)] = [str(c.to_node.id) for c in self.graph.connections if c.from_node == node and c.output_type == "true"]
                    print("True")
                else:
                    state['data'][str(node.id)] = [str(c.to_node.id) for c in self.graph.connections if c.from_node == node and c.output_type == "false"]
                    print("False")
                state["activation"][str(node.id)] = True
                memory_targets = [c.to_node.id for c in self.graph.connections if c.from_node == node and c.to_node.type == 'memory']
                for memory_node_id in memory_targets:
                    file_path = os.path.join(script_dir, f"memory_{memory_node_id}.txt")
                    try:
                        with open(file_path, 'a', encoding='utf-8') as f:
                            f.write(str(state['data'][str(node.id)]) + "\n\n")
                    except (PermissionError, OSError) as e:
                        print(f"Error writing to {file_path}: {e}")
                return state
            return fn

        def query_factory(node: Node):
            def fn(state: Dict[str, Any]) -> Dict[str, Any]:
                incoming = self.graph.get_incoming_edge_nodes(node)
                flag = True
                for i in incoming:
                    if i.type != "condition":
                        if str(i.id) in state['activation'].keys() and not state['activation'][str(i.id)]:
                            flag = False
                        elif str(i.id) not in state['activation'].keys():
                            flag = False
                    else:
                        if str(node.id) not in state["data"][str(i.id)]:
                            flag = False
                if flag:
                    state["activation"][str(node.id)] = True
                    inputs = [str(state['data'][str(i.id)]) for i in incoming if i.type != "condition"]
                    print(f"[Node {node.id} - QUERY] prompt_parts={node.content + inputs}")
                    prompt = "".join(node.content) + "".join(inputs)
                    out = self.llm.invoke([HumanMessage(content=prompt)])
                    print(f"[Node {node.id}] LLM output='{out.content}'")
                    state['data'][str(node.id)] = out.content
                    memory_targets = [c.to_node.id for c in self.graph.connections if c.from_node == node and c.to_node.type == 'memory']
                    for memory_node_id in memory_targets:
                        file_path = os.path.join(script_dir, f"memory_{memory_node_id}.txt")
                        try:
                            with open(file_path, 'a', encoding='utf-8') as f:
                                f.write(str(state['data'][str(node.id)]) + "\n\n")
                        except (PermissionError, OSError) as e:
                            print(f"Error writing to {file_path}: {e}")
                else:
                    state["activation"][str(node.id)] = False
                return state
            return fn

        def memory_factory(node: Node):
            def fn(state: Dict[str, Any]) -> Dict[str, Any]:
                file_path = os.path.join(script_dir, f"memory_{node.id}.txt")
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                except FileNotFoundError:
                    content = ""
                state['data'][str(node.id)] = content
                state['activation'][str(node.id)] = True
                memory_targets = [c.to_node.id for c in self.graph.connections if c.from_node == node and c.to_node.type == 'memory']
                for memory_node_id in memory_targets:
                    file_path = os.path.join(script_dir, f"memory_{memory_node_id}.txt")
                    try:
                        with open(file_path, 'a', encoding='utf-8') as f:
                            f.write(str(state['data'][str(node.id)]) + "\n\n")
                    except (PermissionError, OSError) as e:
                        print(f"Error writing to {file_path}: {e}")
                return state
            return fn

        def output_factory(node: Node):
            def fn(state: Dict[str, Any]) -> Dict[str, Any]:
                incoming = self.graph.get_incoming_edge_nodes(node)
                parts = [state['data'][str(i.id)] for i in incoming if str(i.id) in state['data']]
                print(f"[Node {node.id} - OUTPUT] parts={parts}")
                state['answer'] = "".join(parts)
                state['data'][str(node.id)] = state['answer']
                state["activation"][str(node.id)] = True
                memory_targets = [c.to_node.id for c in self.graph.connections if c.from_node == node and c.to_node.type == 'memory']
                for memory_node_id in memory_targets:
                    file_path = os.path.join(script_dir, f"memory_{memory_node_id}.txt")
                    try:
                        with open(file_path, 'a', encoding='utf-8') as f:
                            f.write(str(state['data'][str(node.id)]) + "\n\n")
                    except (PermissionError, OSError) as e:
                        print(f"Error writing to {file_path}: {e}")
                return state
            return fn

        # Assign functions
        for node in self.graph.nodes:
            if node.type == 'input':
                self.node_funcs[node.id] = input_factory(node)
            elif node.type == 'retrieval':
                self.node_funcs[node.id] = retrieval_factory(node)
            elif node.type == 'query':
                self.node_funcs[node.id] = query_factory(node)
            elif node.type == 'condition':
                self.node_funcs[node.id] = condition_factory(node)
            elif node.type == 'memory':
                self.node_funcs[node.id] = memory_factory(node)
            elif node.type == 'output':
                self.node_funcs[node.id] = output_factory(node)
            else:
                raise ValueError(f"Unsupported node type: {node.type}")

        self.exec_order = self.graph.topological_sort()

    def ask_question(self, question: str) -> str:
        state: Dict[str, Any] = {'question': question, 'data': {}, 'activation': {}, 'answer': ''}
        print(f"Starting workflow for question: '{question}'")
        for nid in self.exec_order:
            print(f"\n---> Executing node {nid} ({self.graph.get_node_by_id(nid).type})")
            state = self.node_funcs[nid](state)
        return str(state['answer'])

def prompt(inp):
    graph = Graph()
    workflow = LLMWorkflow(graph, vector_store, llm)
    workflow.get_graph('graph.json')
    workflow.build()
    ans = workflow.ask_question(inp)
    return ans

if __name__ == '__main__':
    prompt("Hello who are you")
    pass
    #graph = Graph()
    #workflow = LLMWorkflow(graph, vector_store, llm)
    #workflow.get_graph('graph.json')
    #workflow.build()
    #workflow.clear_memory()
    #ans = workflow.ask_question("What are System 1 and System 2?")
    #print(ans)
