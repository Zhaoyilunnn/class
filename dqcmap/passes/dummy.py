# This import is needed for python versions prior to 3.10
from __future__ import annotations

from qiskit.transpiler import PassManager
from qiskit.transpiler.passes import VF2Layout
from qiskit.transpiler.passmanager_config import PassManagerConfig
from qiskit.transpiler.preset_passmanagers import common
from qiskit.transpiler.preset_passmanagers.plugin import PassManagerStagePlugin


class DummyLayoutPlugin(PassManagerStagePlugin):
    def pass_manager(
        self,
        pass_manager_config: PassManagerConfig,
        optimization_level: int | None = None,
    ) -> PassManager:
        layout_pm = PassManager(
            [
                VF2Layout(
                    coupling_map=pass_manager_config.coupling_map,
                    properties=pass_manager_config.backend_properties,
                    max_trials=optimization_level * 10 + 1,
                    target=pass_manager_config.target,
                )
            ]
        )
        layout_pm += common.generate_embed_passmanager(pass_manager_config.coupling_map)
        return layout_pm
