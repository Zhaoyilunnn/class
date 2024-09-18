# This import is needed for python versions prior to 3.10
from __future__ import annotations

from qiskit.passmanager.flow_controllers import ConditionalController
from qiskit.transpiler.exceptions import TranspilerError
from qiskit.transpiler.passes import (
    BarrierBeforeFinalMeasurements,
    SabreLayout,
    SetLayout,
)
from qiskit.transpiler.passmanager import PassManager
from qiskit.transpiler.preset_passmanagers import common
from qiskit.transpiler.preset_passmanagers.plugin import PassManagerStagePlugin

from dqcmap.circuit_prop import CircProperty
from dqcmap.controller import ControllerConfig

from .dm_layout import DqcMapLayout
from .dm_swap import DqcMapSwap


class DqcMapLayoutPlugin(PassManagerStagePlugin):
    def pass_manager(self, pass_manager_config, optimization_level=None) -> PassManager:
        _given_layout = SetLayout(pass_manager_config.initial_layout)

        def _choose_layout_condition(property_set):
            return not property_set["layout"]

        def _swap_mapped(property_set):
            return property_set["final_layout"] is None

        if pass_manager_config.target is None:
            coupling_map = pass_manager_config.coupling_map
        else:
            coupling_map = pass_manager_config.target

        layout = PassManager()
        layout.append(_given_layout)
        if optimization_level == 0:
            layout_pass = SabreLayout(
                coupling_map,
                max_iterations=1,
                seed=pass_manager_config.seed_transpiler,
                swap_trials=5,
                layout_trials=5,
                skip_routing=pass_manager_config.routing_method is not None
                and pass_manager_config.routing_method != "sabre",
            )
        elif optimization_level == 1:
            layout_pass = DqcMapLayout(
                coupling_map,
                max_iterations=2,
                seed=pass_manager_config.seed_transpiler,
                swap_trials=5,
                layout_trials=5,
                skip_routing=pass_manager_config.routing_method is not None
                and pass_manager_config.routing_method != "sabre",
            )
        elif optimization_level == 2:
            layout_pass = SabreLayout(
                coupling_map,
                max_iterations=2,
                seed=pass_manager_config.seed_transpiler,
                swap_trials=20,
                layout_trials=20,
                skip_routing=pass_manager_config.routing_method is not None
                and pass_manager_config.routing_method != "sabre",
            )
        elif optimization_level == 3:
            layout_pass = SabreLayout(
                coupling_map,
                max_iterations=4,
                seed=pass_manager_config.seed_transpiler,
                swap_trials=20,
                layout_trials=20,
                skip_routing=pass_manager_config.routing_method is not None
                and pass_manager_config.routing_method != "sabre",
            )
        else:
            raise TranspilerError(f"Invalid optimization level: {optimization_level}")
        layout.append(
            ConditionalController(
                [
                    BarrierBeforeFinalMeasurements(
                        "qiskit.transpiler.internal.routing.protection.barrier"
                    ),
                    layout_pass,
                ],
                condition=_choose_layout_condition,
            )
        )
        embed = common.generate_embed_passmanager(coupling_map)
        layout.append(
            ConditionalController(embed.to_flow_controller(), condition=_swap_mapped)
        )
        return layout


class DqcMapRoutePlugin(PassManagerStagePlugin):
    """Plugin class for routing stage with :class:`~.DqcMapSwap`"""

    def pass_manager(self, pass_manager_config, optimization_level=None) -> PassManager:
        """Build routing stage PassManager."""
        # check if dqcmap related attributes exist
        ctrl_conf = None
        circ_prop = None
        if hasattr(pass_manager_config, "ctrl_conf") and hasattr(
            pass_manager_config, "circ_prop"
        ):
            ctrl_conf = getattr(pass_manager_config, "ctrl_conf")
            circ_prop = getattr(pass_manager_config, "circ_prop")
            assert isinstance(ctrl_conf, ControllerConfig) and isinstance(
                circ_prop, CircProperty
            )

        seed_transpiler = pass_manager_config.seed_transpiler
        target = pass_manager_config.target
        coupling_map = pass_manager_config.coupling_map
        coupling_map_routing = target
        if coupling_map_routing is None:
            coupling_map_routing = coupling_map
        backend_properties = pass_manager_config.backend_properties
        vf2_call_limit, vf2_max_trials = common.get_vf2_limits(
            optimization_level,
            pass_manager_config.layout_method,
            pass_manager_config.initial_layout,
        )
        if optimization_level == 0:
            routing_pass = DqcMapSwap(
                coupling_map_routing,
                heuristic="basic",
                seed=seed_transpiler,
                trials=5,
            )
            return common.generate_routing_passmanager(
                routing_pass,
                target,
                coupling_map=coupling_map,
                seed_transpiler=seed_transpiler,
                use_barrier_before_measurement=True,
            )
        if optimization_level == 1:
            routing_pass = DqcMapSwap(
                coupling_map_routing,
                heuristic="dqcmap",
                seed=seed_transpiler,
                trials=5,
                ctrl_conf=ctrl_conf,
                circ_prop=circ_prop,
            )
            return common.generate_routing_passmanager(
                routing_pass,
                target,
                coupling_map,
                vf2_call_limit=vf2_call_limit,
                vf2_max_trials=vf2_max_trials,
                backend_properties=backend_properties,
                seed_transpiler=seed_transpiler,
                check_trivial=True,
                use_barrier_before_measurement=True,
            )
        if optimization_level == 2:
            routing_pass = DqcMapSwap(
                coupling_map_routing,
                heuristic="decay",
                seed=seed_transpiler,
                trials=10,
            )
            return common.generate_routing_passmanager(
                routing_pass,
                target,
                coupling_map=coupling_map,
                vf2_call_limit=vf2_call_limit,
                vf2_max_trials=vf2_max_trials,
                backend_properties=backend_properties,
                seed_transpiler=seed_transpiler,
                use_barrier_before_measurement=True,
            )
        if optimization_level == 3:
            routing_pass = DqcMapSwap(
                coupling_map_routing,
                heuristic="decay",
                seed=seed_transpiler,
                trials=20,
            )
            return common.generate_routing_passmanager(
                routing_pass,
                target,
                coupling_map=coupling_map,
                vf2_call_limit=vf2_call_limit,
                vf2_max_trials=vf2_max_trials,
                backend_properties=backend_properties,
                seed_transpiler=seed_transpiler,
                use_barrier_before_measurement=True,
            )
        raise TranspilerError(
            f"Invalid optimization level specified: {optimization_level}"
        )
