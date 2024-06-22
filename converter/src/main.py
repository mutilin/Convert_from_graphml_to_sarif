import xml.etree.ElementTree as ET
import json
import argparse
import re

specification_map = {"G ! call(func())" : {"id": "RO1", "desc" : "The function 'func' is not called in any finite execution of the program."}, 
                     "G valid-free" : {"id": "RO2", "desc" : "All memory deallocations are valid (counterexample: invalid free). More precisely: There exists no finite execution of the program on which an invalid memory deallocation occurs."}, 
                     "G valid-deref" : {"id": "RO3", "desc" : "All pointer dereferences are valid (counterexample: invalid dereference). More precisely: There exists no finite execution of the program on which an invalid pointer dereference occurs."},
                     "G valid-memtrack" : {"id": "RO4", "desc" : "All allocated memory is tracked, i.e., pointed to or deallocated (counterexample: memory leak). More precisely: There exists no finite execution of the program on which the program lost track of some previously allocated memory. (Comparison to Valgrind: This property is violated if Valgrind reports 'definitely lost'.)"}, 
                     "G valid-memcleanup" : {"id": "RO5", "desc" : "All allocated memory is deallocated before the program terminates. In addition to valid-memtrack: There exists no finite execution of the program on which the program terminates but still points to allocated memory. (Comparison to Valgrind: This property can be violated even if Valgrind reports 'still reachable'.)"},
                     "G ! overflow" : {"id": "RO6", "desc" : "It can never happen that the resulting type of an operation is a signed integer type but the resulting value is not in the range of values that are representable by that type."},
                     "G ! data-race" : {"id": "RO7", "desc" : "If there exist two or more concurrent accesses to the same memory location and at least one is a write access, then all accesses must be atomic."},
                     "F end" : {"id": "RO0", "desc" : "Every path finally reaches the end of the program. The proposition 'end' is true at the end of every finite program execution (exit, abort, return from the initial call of main, etc.). A counterexample for this property is an infinite program execution."}}

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

    with open("edges", 'w') as edges_file:
        edges_file.write(str(edges))
    with open("nodes.txt", 'w') as nodes_file:
        nodes_file.write(str(nodes))
    
    return nodes, edges

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

        if new_rule not in runs["tool"]["driver"]["rules"]:
            runs["tool"]["driver"]["rules"].append(new_rule)

    for node_id, node_data in nodes.items():
        node_type = node_data.get('type')
        if node_type == 'entry':
            entry_node = node_id
        elif node_type == 'violation':
            violation_node = node_id

    for source, target, data in edges:

        if 'specification' in data:
            new_specification = data['specification']
            new_formula = re.search(r'LTL\((.*?)\)', new_specification).group(1)
            rule_id = specification_map[formula]["id"],
            short_description = new_specification
            full_description = specification_map[formula]["desc"]

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


        if 'enterFunction' in data or 'returnFromFunction' in data:
            locations = []

            if 'sourcecode' in data:
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

            if 'assumption' in data:
                assumption = data['assumption']
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
                        },
                        "message": {
                            "text": assumption
                        }
                    }
                })

            thread_flows = []
            thread_flows.append({
                "locations": [
                    {
                        "location": {
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
                        }
                    }
                ]
            })

            for run in runs:
                run["results"].append({
                    "ruleId": rule_id,
                    "message": {
                        "text": "Example error trace converted from GraphML"
                    },
                    "locations": locations,
                    "codeFlows": [
                        {
                            "threadFlows": thread_flows
                        }
                    ]
                })

    sarif_log = {
        "version": "2.1.0",
        "runs": runs
    }

    return sarif_log

def main():
    parser = argparse.ArgumentParser(description='Add your own specification')
    parser.add_argument('specification', nargs='?', default=None, help='Optional dependencies')
    
    args = parser.parse_args()
    graphml_file = '../package/witness.graphml'
    nodes, edges = parse_graphml(graphml_file)
    sarif_data = convert_to_sarif(nodes, edges, args.specification)
    
    with open('result.sarif', 'w') as sarif_file:
        json.dump(sarif_data, sarif_file, indent=2)

if __name__ == "__main__":
    main()