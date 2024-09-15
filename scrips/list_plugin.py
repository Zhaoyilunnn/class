from qiskit.transpiler.preset_passmanagers.plugin import list_stage_plugins

print("==================== Installed Layout Plugins ====================")
print(list_stage_plugins("layout"))
print("==================== Installed Route Plugins ====================")
print(list_stage_plugins("routing"))
