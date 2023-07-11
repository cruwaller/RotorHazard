''' FPV Finalnd - FAI based finals geneator '''
# FAI: https://www.fai.org/sites/default/files/ciam/wcup_drones/sc4_vol_f9_dronesport_22_2022-03-01_0.pdf
# MultiGP: https://docs.google.com/document/d/1jWVjCnoIGdW1j_bklrbg-0D24c3x6YG5m_vmF7faG-U/edit#heading=h.hoxlrr3v86bb

import logging
import json
from eventmanager import Evt
from HeatGenerator import HeatGenerator, HeatPlan, HeatPlanSlot, SeedMethod
from RHUI import UIField, UIFieldType, UIFieldSelectOption
from Database import ProgramMethod

logger = logging.getLogger(__name__)

def _logd(dbg: str):
    logger.debug(f"ff.gen: {dbg}")

def _logi(info: str):
    logger.info(f"ff.gen: {info}")

def _logw(wrn: str):
    logger.warning(f"ff.gen WARN: {wrn}")

def _loge(err: str):
    logger.error(f"ff.gen ERROR: {err}")


def _generateHeatPlanSlot(inputs):
    _seeds = []
    for x in inputs:
        if type(x) == tuple:
            _seeds.append(HeatPlanSlot(SeedMethod.HEAT_INDEX, x[1], x[0]))
        else:
            _seeds.append(HeatPlanSlot(SeedMethod.INPUT, x))
    return _seeds


def bracket_2e_8_fai(rhapi):
    _rounds = [
        [1, 4, 5, 8],
        [2, 3, 6, 7],
        [(0, 4), (0, 3), (1, 3), (1, 4)],
        [(0, 2), (0, 1), (1, 1), (1, 2)],
        [(2, 2), (2, 1), (3, 3), (3, 4)],
    ]
    _final = [(3, 2), (3, 1), (4, 1), (4, 2)]

    _plan = []
    for _idx, _input in enumerate(_rounds):
        _plan.append(HeatPlan(rhapi.__('Race') + f" {_idx + 1}", _generateHeatPlanSlot(_input)))
    _plan.append(HeatPlan(rhapi.__('Final'), _generateHeatPlanSlot(_final)))
    return _plan



def bracket_2e_16_fai(rhapi):
    _rounds = [
        [1, 8, 9, 16],
        [4, 5, 12, 13],
        [3, 6, 10, 14],
        [2, 7, 11, 15],
        [(0, 4), (1, 3), (2, 3), (3, 4)],
        [(1, 4), (0, 3), (3, 3), (2, 4)],
        [(0, 2), (0, 1), (1, 1), (1, 2)],
        [(2, 2), (2, 1), (3, 1), (3, 2)],
        [(7, 4), (5, 2), (4, 1), (6, 3)],
        [(6, 4), (4, 2), (5, 1), (7, 3)],
        [(8, 2), (8, 1), (9, 1), (9, 2)],
        [(6, 2), (6, 1), (7, 1), (7, 2)],
        [(11, 4), (10, 2), (10, 1), (11, 3)],
    ]
    _final = [(12, 2), (11, 2), (11, 1), (12, 1)]

    _plan = []
    for _idx, _input in enumerate(_rounds):
        _plan.append(HeatPlan(rhapi.__('Race') + f" {_idx + 1}", _generateHeatPlanSlot(_input)))
    _plan.append(HeatPlan(rhapi.__('Final'), _generateHeatPlanSlot(_final)))
    return _plan


def bracket_2e_std(rhapi, generate_args):
    available_seats = generate_args.get('available_seats')
    num_pilots_per_heat = int(generate_args['num_pilots'])
    standard = generate_args.get('standard', '')

    if not standard:
        return False
    pilot_count = int(standard[3:])

    if standard == 'fai8':
        heats = bracket_2e_8_fai(rhapi)
    elif standard == 'fai16':
        heats = bracket_2e_16_fai(rhapi)
    else:
        _loge(f"Invalid standard...")
        return False

    if 'seed_offset' in generate_args:
        seed_offset = max(int(generate_args['seed_offset']) - 1, 0)
        if seed_offset:
            for heat in heats[:4]:
                for slot in heat['slots']:
                    slot['seed_rank'] += seed_offset

    return heats

# ---------------------------------
# LADDER / LETTER

def _getTotalPilots(rhapi, generate_args):
    input_class_id = generate_args.get('input_class')

    if input_class_id:
        if 'total_pilots' in generate_args:
            total_pilots = int(generate_args['total_pilots'])
        else:
            race_class = rhapi.db.raceclass_by_id(input_class_id)
            class_results = rhapi.db.raceclass_results(race_class)
            if class_results and type(class_results) == dict:
                # fill from available results
                total_pilots = len(class_results['by_race_time'])
            else:
                # fall back to all pilots
                total_pilots = len(rhapi.db.pilots)
    else:
        # use total number of pilots
        total_pilots = len(rhapi.db.pilots)

    return total_pilots

def generateLadder(rhapi, generate_args=None):
    available_seats = generate_args.get('available_seats')
    suffix = rhapi.__(generate_args.get('suffix', 'Main'))

    if generate_args.get('qualifiers_per_heat') and generate_args.get('advances_per_heat'):
        qualifiers_per_heat = int(generate_args['qualifiers_per_heat'])
        advances_per_heat = int(generate_args['advances_per_heat'])
    elif generate_args.get('advances_per_heat'):
        advances_per_heat = int(generate_args['advances_per_heat'])
        qualifiers_per_heat = available_seats - advances_per_heat
    elif generate_args.get('qualifiers_per_heat'):
        qualifiers_per_heat = int(generate_args['qualifiers_per_heat'])
        advances_per_heat = available_seats - qualifiers_per_heat
    else:
        qualifiers_per_heat = available_seats - 1
        advances_per_heat = 1

    if qualifiers_per_heat < 1 or advances_per_heat < 1:
        if not ('advances_per_heat' in generate_args and generate_args['advances_per_heat'] == 0):
            logger.warning("Unable to seed ladder: provided qualifiers and advances must be > 0")
            return False

    total_pilots = _getTotalPilots(rhapi, generate_args)

    if total_pilots == 0:
        logger.warning("Unable to seed ladder: no pilots available")
        return False

    letters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
    heats = []

    if 'seed_offset' in generate_args:
        seed_offset = max(int(generate_args['seed_offset']) - 1, 0)
    else:
        seed_offset = 0

    unseeded_pilots = list(range(seed_offset, total_pilots+seed_offset))
    heat_pilots = 0

    while len(unseeded_pilots):
        if heat_pilots == 0:
            heat = HeatPlan(
                letters[len(heats)] + ' ' + suffix,
                []
            )

        if heat_pilots < qualifiers_per_heat:
            # slot qualifiers
            heat.slots.append(HeatPlanSlot(SeedMethod.INPUT, unseeded_pilots.pop(0) + 1))

            heat_pilots += 1
        else:
            if len(unseeded_pilots) <= advances_per_heat:
                # slot remainder as qualifiers
                for seed in unseeded_pilots:
                    heat.slots.append(HeatPlanSlot(SeedMethod.INPUT, seed + 1))

                unseeded_pilots = [] # empty after using

            else:
                # slot advances
                for adv_idx in range(advances_per_heat):
                    heat.slots.append(HeatPlanSlot(SeedMethod.HEAT_INDEX, adv_idx + 1, -len(heats) - 2))

            heats = [heat, *heats] # insert at front
            heat_pilots = 0

    if heat_pilots: # insert final heat
        heats = [heat, *heats]

    return heats


def register_handlers(args):
    # returns array of exporters with default arguments
    generators = [
        HeatGenerator(
            'FPV Finland, double elimination',
            bracket_2e_std,
            None,
            [
                UIField('standard', "Spec", UIFieldType.SELECT, options=[
                        UIFieldSelectOption('fai8', "FAI, 4-up, 8-pilot"),
                        UIFieldSelectOption('fai16', "FAI, 4-up, 16-pilot"),
                    ], value='fai8'),
                UIField('num_pilots', "Number of Pilots", UIFieldType.BASIC_INT, value=0, desc="0 = disabled"),
                UIField('seed_offset', "Seed from rank", UIFieldType.BASIC_INT, value=1),
            ],
        ),
        HeatGenerator(
            'FPV Finland Letter fill',
            generateLadder,
            None,
            [
                UIField('advances_per_heat', "Advances per heat", UIFieldType.BASIC_INT, value=2),
                UIField('qualifiers_per_heat', "Seeded slots per heat", UIFieldType.BASIC_INT, placeholder="Auto"),
                UIField('total_pilots', "Pilots in class", UIFieldType.BASIC_INT, placeholder="Auto", desc="Used only with input class"),
                UIField('seed_offset', "Seed from rank", UIFieldType.BASIC_INT, value=1),
                UIField('suffix', "Heat title suffix", UIFieldType.TEXT, placeholder="Main", value="Main"),
            ]
        ),
    ]
    for generator in generators:
        args['register_fn'](generator)

def initialize(rhapi):
    rhapi.events.on(Evt.HEAT_GENERATOR_INITIALIZE, register_handlers)
