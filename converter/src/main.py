import uuid
import xml.etree.ElementTree as ET
import json

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

def convert_to_sarif(nodes, edges):
    sarif = {
        "shema"
        "version": "2.1.0",
        "runs": [{
            "tool": {
                "driver": {
                    "name": "Witness GraphML to SARIF Converter",
                    "informationUri": "https://github.com/sosy-lab/sv-witnesses",
                    "rules": []
                }
            },
            "results": [],
            "invocations": [],
            "threadFlowLocations": [],
            "properties": {}
        }]
    }
    
    result = {
        "ruleId": uuid.uuid4(),
        "level": "error",
        "message": {
            "text": "Error trace from Witness"
        },
        "locations": [],
        "codeFlows": [{
            "threadFlows": [{
                "locations": []
            }]
        }]
    }

    for node_id, node_data in nodes.items():
        if node_data.get('violation'):
            result['locations'].append({
                "physicalLocation": {
                    "artifactLocation": {
                        "uri": node_data.get('sourcecode')
                    },
                    "region": {
                        "startLine": int(node_data.get('startline', 1)),
                        "endLine": int(node_data.get('endline', 1)),
                        "startColumn": int(node_data.get('startoffset', 1)),
                        "endColumn": int(node_data.get('endoffset', 1))
                    }
                }
            })
        sarif['runs'][0]['results'].append(result)
    
    for source, target, edge_data in edges:
        thread_flow_location = {
            "location": {
                "physicalLocation": {
                    "artifactLocation": {
                        "uri": nodes[source].get('sourcecode')
                    },
                    "region": {
                        "startLine": int(edge_data.get('startline', 1)),
                        "endLine": int(edge_data.get('endline', 1)),
                        "startColumn": int(edge_data.get('startoffset', 1)),
                        "endColumn": int(edge_data.get('endoffset', 1))
                    }
                }
            },
            "threadFlowLocation": {
                "kinds": ["function"] if 'enterFunction' in edge_data else [],
                "executionOrder": int(edge_data.get('executionOrder', 0))
            }
        }
        #sarif['runs'][0]['results']['codeFlows'][0]['threadFlows'][0]['locations'].append(thread_flow_location)
    
    return sarif

def main():
    graphml_file = '../package/witness.graphml'
    nodes, edges = parse_graphml(graphml_file)
    sarif_data = convert_to_sarif(nodes, edges)
    
    with open('result.sarif', 'w') as sarif_file:
        json.dump(sarif_data, sarif_file, indent=2)

if __name__ == "__main__":
    main()