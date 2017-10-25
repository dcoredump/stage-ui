#!/usr/bin/python3
from pluginsmanager.banks_manager import BanksManager
from pluginsmanager.model.bank import Bank
#from pluginsmanager.model.connection import Connection
#from pluginsmanager.model.midi_connection import MidiConnection
#from pluginsmanager.observer.autosaver.autosaver import Autosaver
from pluginsmanager.observer.mod_host.mod_host import ModHost
from pluginsmanager.model.pedalboard import Pedalboard
from pluginsmanager.model.lv2.lv2_effect_builder import Lv2EffectBuilder
from pluginsmanager.model.system.system_effect import SystemEffect
from pluginsmanager.model.system.system_effect_builder import SystemEffectBuilder
from pluginsmanager.jack.jack_client import JackClient

client = JackClient()
jack_system = SystemEffect(
    'system',
    [],                             # audio inputs
    ['playback_1', 'playback_2'],    # audio output
    [],            # midi inputs
    []            # midi outputs
)
jack_ttymidi = SystemEffect(
    'ttymidi',
    [],    # audio inputs
    [],    # audio output
    ['MIDI_in'],    # midi inputs
    ['MIDI_out']     # midi outputs
)

modhost = ModHost('localhost')
modhost.connect()

#manager = BanksManager()
#manager.register(modhost)

pedalboard = Pedalboard('MDA-EP')
builder = Lv2EffectBuilder()
builder.reload(builder.lv2_plugins_data())
ep = builder.build('http://moddevices.com/plugins/mda/EPiano')
#ep = builder.build('https://github.com/dcoredump/dexed.lv2')
#ep = builder.build('http://tytel.org/helm')

# REMEMBER: FIRST OUTPUT, SECOND INPUT
# EPiano contains two audio output ports and one midi input port
pedalboard.connect(ep.outputs[0],jack_system.inputs[0])
#pedalboard.connect(ep.outputs[1],jack_system.inputs[1])
pedalboard.connect(jack_ttymidi.midi_outputs[0],ep.midi_inputs[0])

modhost.pedalboard = pedalboard

print("Running...")

# Safe close
from signal import pause
try:
    pause()
except KeyboardInterrupt:
    modhost.close()
