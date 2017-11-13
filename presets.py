#!/usr/bin/python3

import lilv
from collections import defaultdict
import pprint
import sys

world = lilv.World()
world.load_all()

def get_plugin_presets(plugin_name):
    global world

    plugin_presets=defaultdict(list)
    plugin = world.get_all_plugins().get_by_uri(world.new_uri(plugin_name))
    preset_uri = lilv.Node(world.new_uri("http://lv2plug.in/ns/ext/presets#Preset"))
    psets = plugin.get_related(preset_uri)
    label_uri = world.new_uri(lilv.LILV_NS_RDFS + "label")

    print("Plugin: %s (%s)" % (plugin.get_uri(),plugin.get_name()))

    for pset_node in psets:
        pset_nodes=world.find_nodes(pset_node,label_uri,None)
        for pset_name in pset_nodes:
            #plugin_presets[str(plugin.get_uri())].append((pset_node.get_turtle_token(),pset_name.get_turtle_token()))
            plugin_presets[str(plugin.get_uri())].append((str(pset_node),pset_name.get_turtle_token()))

    return(plugin_presets)

if(__name__=="__main__"):
    pp=defaultdict(list)
    pp=get_plugin_presets(sys.argv[1])
    plugin=defaultdict(list)

    for plugin in pp:
        print(plugin)
        for preset in pp[plugin]:
            print(preset[0]+":"+preset[1])
