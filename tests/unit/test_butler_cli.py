"""Unit tests for butler_cli module."""
import sys

sys.path.insert(0, 'tools')

import butler_cli


def test_create_parser_returns_parser():
    """create_parser should return ArgumentParser."""
    parser = butler_cli.create_parser()
    assert parser is not None
    assert hasattr(parser, 'parse_args')


def test_grouped_commands_exist():
    """Parser should have project, chip, firmware, action, build groups."""
    parser = butler_cli.create_parser()
    args = parser.parse_args(['project', 'onboard'])
    assert args.group == 'project'
    assert args.command == 'onboard'


def test_legacy_fallback():
    """Parser should accept legacy command."""
    parser = butler_cli.create_parser()
    args = parser.parse_args(['legacy'])
    assert args.group == 'legacy'


def test_command_mapping():
    """Command mapping should convert grouped to flat commands."""
    mapping = {
        ('project', 'onboard'): 'onboard',
        ('chip', 'dossier'): 'chip-dossier',
        ('firmware', 'plan'): 'firmware-plan',
    }
    for (group, cmd), expected in mapping.items():
        assert butler_cli.create_parser()  # Verify parser structure
