#!/usr/bin/python3

#PLUGIN="https://github.com/dcoredump/dexed.lv2"
PLUGIN="http://tytel.org/helm"

import lilv
import pprint

world = lilv.World()
world.load_all()

preset_uri = lilv.Node(world.new_uri("http://lv2plug.in/ns/ext/presets#Preset"))
label_uri = world.new_uri(lilv.LILV_NS_RDFS + "label")

print("#!/usr/bin/python3")
print("from collections import defaultdict")
print("plugins={}")
print("plugin_presets=defaultdict(list)\n")

for plugin in world.get_all_plugins():
    
    #print(plugin.get_uri().as_string())
    #plugin = world.get_all_plugins().get_by_uri(world.new_uri(PLUGIN))
    #psets = plugin.get_related(preset_uri)
    #pprint.pprint(plugin.get_value(plugin.get_name()))
    print("plugins[\'%s\']={}" % (plugin.get_uri()))
    print("plugins[\'%s\'][\'name\']=\'%s\'" % (plugin.get_uri(),plugin.get_name()))
    psets = plugin.get_related(plugin.get_uri())
    for pset_node in psets:
        #print("pset_node.get_turtle_token())
        pset_nodes=world.find_nodes(pset_node,label_uri,None)
        for pset_name in pset_nodes:
            #print(pset_name.get_turtle_token())
            print("plugin_presets[\'%s\'].append((\'%s\',\'%s\'))" % (plugin.get_uri(),pset_node.get_turtle_token(),pset_name.get_turtle_token()))
