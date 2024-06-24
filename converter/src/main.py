import xml.etree.ElementTree as ET
import json
import argparse
import re
import sys

specification_map = {"G ! call(func())" : {"id": "RO1", "desc" : "The function 'func' is not called in any finite execution of the program."}, 
                     "G valid-free" : {"id": "RO2", "desc" : "All memory deallocations are valid (counterexample: invalid free). More precisely: There exists no finite execution of the program on which an invalid memory deallocation occurs."}, 
                     "G valid-deref" : {"id": "RO3", "desc" : "All pointer dereferences are valid (counterexample: invalid dereference). More precisely: There exists no finite execution of the program on which an invalid pointer dereference occurs."},
                     "G valid-memtrack" : {"id": "RO4", "desc" : "All allocated memory is tracked, i.e., pointed to or deallocated (counterexample: memory leak). More precisely: There exists no finite execution of the program on which the program lost track of some previously allocated memory. (Comparison to Valgrind: This property is violated if Valgrind reports 'definitely lost'.)"}, 
                     "G valid-memcleanup" : {"id": "RO5", "desc" : "All allocated memory is deallocated before the program terminates. In addition to valid-memtrack: There exists no finite execution of the program on which the program terminates but still points to allocated memory. (Comparison to Valgrind: This property can be violated even if Valgrind reports 'still reachable'.)"},
                     "G ! overflow" : {"id": "RO6", "desc" : "It can never happen that the resulting type of an operation is a signed integer type but the resulting value is not in the range of values that are representable by that type."},
                     "G ! data-race" : {"id": "RO7", "desc" : "If there exist two or more concurrent accesses to the same memory location and at least one is a write access, then all accesses must be atomic."},
                     "F end" : {"id": "RO0", "desc" : "Every path finally reaches the end of the program. The proposition 'end' is true at the end of every finite program execution (exit, abort, return from the initial call of main, etc.). A counterexample for this property is an infinite program execution."}}

def dfs_find_path(entry_node, nodes, edges, all_edges, violation_node):
    stack = [entry_node]
    visited = set()
    parent = {entry_node: None}

    while stack:
        node = stack.pop()

        # Если нашли конечную вершину, восстановим путь
        if node == violation_node:
            path = []
            while node is not None:
                path.append(node)
                node = parent[node]
            path.reverse()
            break

        # Если вершина еще не была посещена
        if node not in visited:
            visited.add(node)

            # Добавление соседних вершин в стек
            for target, data in edges[node]:
                if target not in visited and "sink" not in nodes[target]:
                    stack.append(target)
                    parent[target] = node
    
    graph_edges = {}
    for source, target, data in all_edges:
        if source not in graph_edges and source in path:
            graph_edges[source] = []
        index = path.index(source)
        if target == path[index + 1]:
            graph_edges[source].append((target, data))
    return path, graph_edges

def parse_graphml(graphml_file):
    tree = ET.parse(graphml_file)
    root = tree.getroot()
    ns = {'graphml': 'http://graphml.graphdrawing.org/xmlns'}
    
    nodes = {}
    edges = []
    
    for node in root.findall('.//graphml:node', ns):
        node_id = node.get('id')
        data = {}
        for data_elem in node.findall('graphml:data', ns):
            key = data_elem.get('key')
            value = data_elem.text
            data[key] = value
        nodes[node_id] = data
    
    for edge in root.findall('.//graphml:edge', ns):
        source = edge.get('source')
        target = edge.get('target')
        data = {}
        for data_elem in edge.findall('graphml:data', ns):
            key = data_elem.get('key')
            value = data_elem.text
            data[key] = value
        edges.append((source, target, data))


def convert_to_sarif(nodes, edges, specification=None):
    runs = []
    parametr_rule_id = None
    runs.append({
                "tool": {
                    "driver": {
                        "name": "SV-COMP Witness Converter",
                        "version": "2.1.0",
                        "informationUri": "https://github.com/sosy-lab/sv-witnesses",
                        "rules": []
                    }
                },
                "results": []
            })
    
    if specification is not None:
        formula = re.search(r'LTL\((.*?)\)', specification).group(1)
        parametr_rule_id = specification_map[formula]["id"]
        new_rule = {
                "id": parametr_rule_id,
                "shortDescription": {
                    "text": specification
                },
                "fullDescription": {
                    "text": specification_map[formula]["desc"]
                }           
        }

        if new_rule not in runs[0]["tool"]["driver"]["rules"]:
            runs[0]["tool"]["driver"]["rules"].append(new_rule)

    entry_node = None
    violation_node = None
    visited = {}
    graph_edges = {}
    for source, target, data in edges:
        if source not in graph_edges:
            graph_edges[source] = []
        graph_edges[source].append((target, data))
    with open("gedges", 'w') as gedges_file:
        for src, data in graph_edges.items():
            gedges_file.write(src + " " + str(data[0]) + "\n")
    for node_id, node_data in nodes.items():
        visited[node_id] = False
        node_type_e = node_data.get('entry')
        if node_type_e == 'true':
            entry_node = node_id
        node_type_v = node_data.get('violation')
        if node_type_v == 'true':
            violation_node = node_id

    path, graph_edges = dfs_find_path(entry_node=entry_node, nodes=nodes, edges=graph_edges, all_edges=edges, violation_node=violation_node)
    stacks = []
    stacks_node = []
    thread_flows = []
    locations = []

    codeFlows_json = [{
        "message" : {
            "text" : "Path to error"
        },
        "threadFlows": [{
            "locations" : []
        }]
    }]
    for current_node in path:
        if current_node == violation_node:
            locations.append({
                "physicalLocation": {
                    "artifactLocation": {
                        "uri": data.get('originfile')
                    },
                    "region": {
                        "startLine": int(data.get('startline', 0)),
                        "endLine": int(data.get('endline', 0)),
                        "startColumn": int(data.get('startoffset', 0)),
                        "endColumn": int(data.get('endoffset', 0)),
                    }
                }
            })
        else:
            data = graph_edges[current_node][0][1]


            if 'enterFunction' in data:
                stacks_node.append(current_node)
            elif 'returnFrom' in data:
                stacks_node.pop()

            if parametr_rule_id:
                rule_id = parametr_rule_id
            else:
                rule_id = ""

            if 'specification' in data:
                new_specification = data['specification']
                new_formula = re.search(r'LTL\((.*?)\)', new_specification).group(1)
                rule_id = specification_map[new_formula]["id"],
                short_description = new_specification
                full_description = specification_map[new_formula]["desc"]

                new_rule = {
                    "id": rule_id,
                    "shortDescription": {
                        "text": short_description
                    },
                    "fullDescription": {
                        "text": full_description
                    }
                }

                if new_rule not in runs["tool"]["driver"]["rules"]:
                    runs["tool"]["driver"]["rules"].append(new_rule)

            assumption = data.get('assumption', '')
            codeFlows_json[0]["threadFlows"][0]["locations"].append({
                        "location": {
                            "physicalLocation": {
                                "artifactLocation": {
                                    "uri": data.get('originfile')
                                },
                                "region": {
                                    "startLine": int(data.get('startline', 0)),
                                    "endLine": int(data.get('endline', 0)),
                                    #"startColumn": int(data.get('startoffset', 0)),
                                    "endColumn": int(data.get('endoffset', 0)),
                                }
                            },
                            "message": {
                                "text": data.get('sourcecode', "")
                            }
                        },
            })
            #sarif['runs'][0]['results']['codeFlows'][0]['threadFlows'][0]['locations'].append(thread_flow_location)

    stacks_json = {
        "message": {
            "text" : "Resulting call stack"
        },
        "frames": []
    }
    stacks_node.reverse()
    for node in stacks_node:
        stacks_json["frames"].append({
            "location" : {
                "physicalLocation" : {
                    "artifactLocation" : {
                        "uri" : graph_edges[node][0][1].get('originfile')
                    },
                    "region" : {
                        "startLine": int(graph_edges[node][0][1].get('startline', 0)),
                        "startColumn": int(graph_edges[node][0][1].get('startoffset', 0))
                    }
                },
                "logicalLocations": [
                      {
                        "fullyQualifiedName": graph_edges[node][0][1].get('enterFunction', "")
                      }
                ]
            },
            "threadId" : int(data.get('threadId', 0))
        })

    stacks.append(stacks_json)
    for run in runs:
        run["results"].append({
            "ruleId": rule_id,
            "message": {
                "text": "Example error trace converted from GraphML"
            },
            "locations": locations,
            "stacks" : stacks,
            "codeFlows": codeFlows_json
        })
    with open("funcedges", 'w') as funcedges_file:
        for src, data in graph_edges.items():
            if src in stacks:
                funcedges_file.write(src + " " + str(data[0]) + "\n")

    sarif_log = {
        "version": "2.1.0",
        "runs": runs
    }

    return sarif_log

def main():
    parser = argparse.ArgumentParser(description='Add your own specification')
    parser.add_argument('specification', nargs='?', default=None, help='Optional dependencies')
    
    args = parser.parse_args()
    graphml_file1 = 'converter/package/test1/witness1.graphml'
    graphml_file2 = 'converter/package/test2/witness2.graphml'
    graphml_file3 = 'converter/package/test3/witness3.graphml'
    graphml_file4 = 'converter/package/test3/witness3.graphml'
    nodes, edges = parse_graphml(graphml_file1)
    sarif_data = convert_to_sarif(nodes, edges, args.specification)
    
    with open('converter/package/test1/result.sarif', 'w') as sarif_file:
        json.dump(sarif_data, sarif_file, indent=2)

if __name__ == "__main__":
    main()