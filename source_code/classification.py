'''
Classification of intersections.

API:
    + classify_based_on_rules() - classifies intersections following the list of rules.
    + run_graphviz() - builds the graph representing the classification tree for visualization in Graphviz.

'''

import sys
import logging
import csv
import numpy as np
import matplotlib.pyplot as plt
from ast import literal_eval
import posixpath
import graphviz


logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s %(levelname)s %(message)s',
                    stream=sys.stdout,
                    #filename='mylog.log',
                    filemode='w+')





# ==============================================================================
# Auxiliary functions
# ==============================================================================
def labels2str(label_path):
    '''
    Concatenate labels into a string.

    :param label_path: List of labels.

    :return: String with concatenated labels.
    '''

    buf = ''

    for lp in label_path:
        buf += "/{}".format(lp)

    return buf



def get_all_leaf_nodes(node, label_path):
    '''
    Extract all leaf nodes from the classification tree.

    :param node:
    :param label_path:

    :return: List of leaf nodes and the list of label paths.
    '''

    leaf_nodes = []
    label_paths = []

    if 'labels' not in node.keys() or len(node['labels']) == 0:
        leaf_nodes.append(node)
        if len(label_path) > 0:
            label_paths.append(label_path)
    else:
        for l in node['labels']:
            child_label_path = list(label_path)
            child_label_path.append("{}".format(l))
            leaf_nodes_from_subtree, label_paths_from_subtree = get_all_leaf_nodes(node[l], child_label_path)
            leaf_nodes.extend(leaf_nodes_from_subtree)
            label_paths.extend(label_paths_from_subtree)

    return leaf_nodes, label_paths



def classify_by_rule(intersections, tree, rule, debug=False):
    '''
    Subcategorize the leafs of the decision tree based on the given rule.

    :param intersections: List of dictionaries with intersection descriptions.
    :param tree: Classification tree.
    :param rule: Rule {param, type, num_classes, labels, thresholds}.
    :param debug: True - print debug info; False - otherwise.

    :return tree: Updated classification tree.
    '''

    param = rule['param']
    type = rule['type']
    num_classes = rule['num_classes']
    my_labels = rule['labels']
    thresholds = rule['thresholds']

    leaf_nodes, label_paths = get_all_leaf_nodes(tree, [])
    sz = len(leaf_nodes)

    for n in range(sz):
        node = leaf_nodes[n]
        id_prefix = ""
        if len(label_paths) > 0 and len(label_paths[n]) > 0:
            id_prefix = labels2str(label_paths[n])
        labels = []
        if num_classes <= 0 or type == "string" or type == "bool":
            for i in node['intersection_index_set']:
                v = intersections[i][param]
                if v in node.keys():
                    node[v]['intersection_index_set'].add(i)
                else:
                    labels.append(v)
                    node[v] = {'id': "{}/{}".format(id_prefix, v), 'level': node['level']+1, 'intersection_index_set': set([i])}
        else:
            min_v, max_v = intersections[0][param], intersections[0][param]
            for x in intersections:
                min_v, max_v = np.min([min_v, x[param]]), np.max([max_v, x[param]])
            if len(my_labels) != num_classes:
                my_labels = [i for i in range(num_classes)]
            if len(thresholds) != num_classes - 1:
                thresholds = np.linspace(min_v, max_v, num=num_classes+1)
                thresholds = list(thresholds)
                del thresholds[0]
                del thresholds[-1]

            for i in node['intersection_index_set']:
                v = intersections[i][param]
                my_label = None
                for j in range(num_classes - 1):
                    if v <= thresholds[j]:
                        my_label = my_labels[j]
                        break
                if my_label == None:
                    my_label = my_labels[-1]
                if my_label in node.keys():
                    node[my_label]['intersection_index_set'].add(i)
                else:
                    labels.append(my_label)
                    node[my_label] = {'id': "{}/{}".format(id_prefix, my_label), 'level': node['level']+1, 'intersection_index_set': set([i])}

        node['labels'] = labels
        node['rule_name'] = param

    return tree



def traverse_tree(node):
    '''
    Traverse the classification tree to generate a list of (father, child, edge_label) tuples.

    :param node:

    :return: List of the above-mentioned tuples and a list of all nodes.
    '''

    connectivity_list = []
    node_list = []

    if 'labels' in node.keys() and len(node['labels']) > 0:
        for l in node['labels']:
            connectivity_list.append((node, node[l], l))
            node_list.append(node)
            connectivity_sublist, node_sublist = traverse_tree(node[l])
            connectivity_list.extend(connectivity_sublist)
            node_list.extend(node_sublist)
    else:
        node_list.append(node)

    return connectivity_list, node_list



def get_count_range(nodes):
    '''
    Get the range intersection counts in the given list of classification tree nodes.

    :param nodes: List of classification tree nodes.

    :return: [min_count, max_count].
    '''

    min_count, max_count = len(nodes[0]['intersection_index_set']), len(nodes[0]['intersection_index_set'])

    for n in nodes:
        min_count = np.min([min_count, len(n['intersection_index_set'])])
        max_count = np.max([max_count, len(n['intersection_index_set'])])

    return [min_count, max_count]



def get_color(cnt, cnt_range, cmap):
    '''
    Calculate the color for a given value in the given range using a given colormap

    :param cnt: Value, for which we need the color.
    :param cnt_range: Value range.
    :param cmap: Colormap.

    :return: RGB color description in the format "#%2x%2x%2x".
    '''

    if cmap == None:
        return "#FFFFFF"

    c = 255
    clrmap = plt.cm.get_cmap(cmap)
    clr = clrmap(float(cnt) / cnt_range[1])
    color = "#{:02X}{:02X}{:02X}80".format(int(c * clr[0]), int(c * clr[1]), int(c * clr[2]))
    #color += ":#FFFFFF"

    return color





#==============================================================================
# API
#==============================================================================
def classify_based_on_rules(args):
    '''
    Run rule-based classifier specified in a CSV file on the list of intersections given in another CSV file.

    :param args:
        Dictionary with function arguments:
            args['classifier_spec'] = Name of the CSV file with the rule-based classifier spec.
            args['intersections_file'] = Name of the CSV file listing intersections with their parameters.
            args['debug'] = (Optional) Boolean parameter indicating whether DEBUG info must be logged.

    :returns res:
        Dictionary with resulting info:
            res['intersections'] = List of categorized intersections.
                                   Each intersection is represented by a dictionary, containing its cross streets,
                                   geo coordinates and other parameters specified in the intersections CSV file.
            res['rules'] = List of classification rules, which define the classification tree.
            res['num_classes'] = Number of intersection classes.
            res['tree'] = Dictionary representing a classification tree. Each element of the tree is a subtree or a leaf:
                res['tree']['id'] = Node ID.
                res['tree']['rule_name'] = Name of the parameter used for sub-classification.
                res['tree']['intersection_index_set'] = Set of intersection indices belonging to this tree.
                res['tree']['labels'] = (Optional) List of labels resulting from sub-classification.
                res['tree'][<label 1>] = (Optional) Subtree corresponding to label 1.
                ...
                res['tree'][<label n>] = (Optional) Subtree corresponding to label n.
            res['count_ranges'] = List of intersection count ranges of the form [min_count, max_count].
                                  Each range corresponds to its tree level. The size of the lists equals the number
                                  of classification tree levels.
    '''

    if args == None:
        return None

    classifier_spec = args['classifier_spec']
    intersections_file = args['intersections_file']

    debug = False
    if 'debug' in args.keys():
        debug = args['debug']

    with open(classifier_spec, 'r') as f:
        reader = csv.reader(f)
        #next(reader)  # skip header
        specs = [r for r in reader]
        f.close()

    rules = []
    rule_dict = dict()
    for s in specs:
        param = s[0]
        type = s[1]
        num_classes = int(s[2])
        labels, thresholds = [], []
        if len(s) >= 4 and len(s[3]) > 0:
            labels = literal_eval(s[3])
            if len(s) >= 5 and len(s[4]) > 0:
                thresholds = literal_eval(s[4])
        rules.append({'param': param, 'type': type, 'num_classes': num_classes, 'labels': labels, 'thresholds': thresholds})
        rule_dict[param] = {'type': type, 'num_classes': num_classes, 'labels': labels, 'thresholds': thresholds}

    with open(intersections_file, 'r') as f:
        reader = csv.reader(f)
        header = next(reader)
        x_data = [r for r in reader]
        f.close()

    sz = len(header)
    param2idx = dict()
    for i in range(3, sz):
        param2idx[header[i]] = i

    intersections = []
    for l in x_data:
        x = {'cross_streets': literal_eval(l[0]), 'longitude': float(l[1]), 'latitude': float(l[2])}
        for p in param2idx.keys():
            v = l[param2idx[p]]
            if p in rule_dict.keys():
                type = rule_dict[p]['type']
                if type in ['int', 'long', 'float', 'bool']:
                    v = eval(type + "(v)")
            x[p] = v
        intersections.append(x)
    sz = len(intersections)
    idx_list = [i for i in range(sz)]
    intersection_index_set = set(idx_list)

    count_ranges = [[1, sz]]
    tree = {'id': 'top', 'level': 0, 'intersection_index_set': intersection_index_set}

    for r in rules:
        if debug:
            logging.debug("classification.classify_based_on_rules(): Applying rule '{}' at level {} (type={}, num_classes={})...".format(r['param'], len(count_ranges)-1, r['type'], r['num_classes']))
        tree = classify_by_rule(intersections, tree, r, debug=debug)
        leaf_nodes, label_paths = get_all_leaf_nodes(tree, [])
        count_ranges.append(get_count_range(leaf_nodes))

    res = {'intersections': intersections, 'rules': rules, 'tree': tree, 'count_ranges': count_ranges}

    return res



def run_graphviz(args):
    '''
    Build the graph representing the classification tree for visualization in Graphviz.

    :param args:
        Dictionary with function arguments:
            args['tree'] = Dictionary representing a classification tree. Each element of the tree is a subtree or a leaf:
                args['tree']['id'] = Node ID.
                args['tree']['rule_name'] = Name of the parameter used for sub-classification.
                args['tree']['intersection_index_set'] = Set of intersection indices belonging to this tree.
                args['tree']['labels'] = (Optional) List of labels resulting from sub-classification.
                args['tree'][<label 1>] = (Optional) Subtree corresponding to label 1.
                ...
                args['tree'][<label n>] = (Optional) Subtree corresponding to label n.
            args['count_ranges'] = List of intersection count ranges of the form [min_count, max_count].
                                   Each range corresponds to its tree level. The size of the lists equals the number
                                   of classification tree levels.
            args['name'] = Name of the graph that is to be generated.
            args['graphviz_file'] = Name of the Graphviz file where the generated graph will be saved in DOT format.
            args['data_dir'] = Name of the data directory where the output should be placed.
            args['render_format'] = (Optional) Format of the graphical output. Default = 'svg'.
            args['colormap'] = (Optional) Color map defining the color coding of the tree nodes.
                               See matplotlib.cm.get_cmap() for color map options. Default = None.
            args['debug'] = (Optional) Boolean parameter indicating whether DEBUG info must be logged.

    :return: Graphviz object with thegraph representation of the classification tree.
    '''

    tree = args['tree']
    count_ranges = args['count_ranges']
    name = args['name']
    graphviz_file = args['graphviz_file']
    data_dir = args['data_dir']

    render_format = 'svg'
    if 'render_format' in args.keys():
        render_format = args['render_format']

    colormap = None
    if 'colormap' in args.keys():
        colormap = args['colormap']

    debug = False
    if 'debug' in args.keys():
        debug = args['debug']

    if debug:
        logging.debug("classification.run_graphviz(): Creating Graphviz representation of the classification tree '{}'...".format(name))

    links, nodes = traverse_tree(tree)

    g = graphviz.Digraph(name, filename=graphviz_file, directory=data_dir, format=render_format, engine="dot")
    g.attr("graph", rankdir="LR")
    g.attr("node", shape="record")
    g.attr("node", style="filled")

    for n in nodes:
        cnt = len(n['intersection_index_set'])
        cnt_range = count_ranges[n['level']]
        clr = get_color(cnt, cnt_range, cmap=colormap)
        my_id = n['id']
        prm = my_id
        if 'rule_name' in n.keys():
            prm = n['rule_name']
        datum = "<f0> {}|<f1> {}".format(cnt, prm)
        if colormap == None:
            g.node(my_id, datum)
        else:
            g.node(my_id, datum, fillcolor=clr, gradientangle='45')


    for l in links:
        o, d = l[0]['id'], l[1]['id']
        label = "{}".format(l[2])
        g.edge(o, d, label=label)

    if debug:
        logging.debug("classification.run_graphviz(): Generating '{}'...".format(graphviz_file))
    g.save()

    if debug:
        logging.debug("classification.run_graphviz(): Generating '{}.{}'...".format(graphviz_file, render_format))
    g.render()

    return g









# ==============================================================================
# Main function - for standalone execution.
# ==============================================================================

def main(argv):
    print(__doc__)

    maps_dir = "maps"
    rule_files = ["classification_rules.csv", "simple_rules.csv", "adjusted_rules.csv", "adjusted_simplified_rules.csv"]
    classifier_spec = rule_files[3]
    intersections_files = ["San Francisco, California, USA_signalized.csv",
                           "San Francisco, California, USA_nosignal.csv",
                           "San Francisco, California, USA_other.csv"]
    intersections_file = intersections_files[0]
    graphviz_name = "Classification Tree for '{}' using spec '{}'".format(intersections_file, classifier_spec)
    graphviz_file = intersections_file.rsplit(".", 1)[0] + "({}).gv".format(classifier_spec)
    data_dir = "intersections"
    render_format = "svg"
    debug = True

    args = {'classifier_spec': posixpath.join(maps_dir, classifier_spec),
            'intersections_file': posixpath.join(maps_dir, intersections_file),
            'debug': debug}
    res = classify_based_on_rules(args)

    args = {'tree': res['tree'],
            'count_ranges': res['count_ranges'],
            'name': graphviz_name,
            'graphviz_file': graphviz_file,
            'data_dir': data_dir,
            'render_format': render_format,
            'colormap': "jet",
            'debug': debug}
    run_graphviz(args)






if __name__ == "__main__":
    main(sys.argv)