import os
import sys
import json
import tkinter as tk
from unittest.mock import MagicMock, patch
import pytest
import pandas as pd

# --- Configuración de sys.path para encontrar los módulos del proyecto ---
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from modals.simulation_strategies_modal import SimulationStrategiesModal

# --- Constantes y Rutas ---
STRATEGIES_DIR = os.path.join(PROJECT_ROOT, 'strategies')
OUTPUT_CONFIG_PATH = os.path.join(STRATEGIES_DIR, 'strategies.json')

@pytest.fixture
def mock_modal(monkeypatch):
    """Fixture para crear una instancia mockeada del SimulationStrategiesModal."""
    # Mockear el método _build_ui para que no se ejecute y cree la UI
    monkeypatch.setattr(SimulationStrategiesModal, "_build_ui", lambda s: None)

    # Mockear messagebox para que no aparezcan pop-ups durante el test
    monkeypatch.setattr('modals.simulation_strategies_modal.messagebox', MagicMock())

    # Crear mocks para los argumentos del constructor
    mock_parent = MagicMock() 
    mock_logger = MagicMock()
    mock_candles_df = pd.DataFrame({'close': [1, 2, 3]})

    # Instanciar el modal (su UI no se construirá gracias a los mocks)
    modal = SimulationStrategiesModal(mock_parent, mock_candles_df, mock_logger)
    
    # --- Inicialización manual de atributos creados en _build_ui --- #
    modal.strategies_config = {}
    modal.custom_configs = {}
    modal.result = None
    
    # Slots
    modal.slots_forex_var = tk.IntVar(value=1)
    modal.slots_candles_var = tk.IntVar(value=1)

    # Forex Widgets
    modal.forex_widgets = {}
    for strategy_name in modal.forex_strategies:
        modal.forex_widgets[strategy_name] = {
            'checkbox_var': tk.BooleanVar(),
            'percent_ratio_var': tk.DoubleVar(value=1.0),
            'rr_ratio_var': tk.DoubleVar(value=2.0),
            'sl_var': tk.DoubleVar(value=20.0)
        }

    # Candle Widgets
    modal.candle_widgets = {}
    for pattern_name in modal.candle_patterns:
        modal.candle_widgets[pattern_name] = {
            'checkbox_var': tk.BooleanVar(),
            'strategy_var': tk.StringVar(value="Default"),
            'load_button': MagicMock() 
        }

    # Mockear métodos de Toplevel que podrían ser llamados y causar problemas
    monkeypatch.setattr(modal, "destroy", lambda: None)
    monkeypatch.setattr(modal, "grab_set", lambda: None)
    monkeypatch.setattr(modal, "wait_window", lambda: None)

    # Limpiar el archivo de configuración de salida antes del test
    if os.path.exists(OUTPUT_CONFIG_PATH):
        os.remove(OUTPUT_CONFIG_PATH)

    yield modal

    # Limpieza después del test
    if os.path.exists(OUTPUT_CONFIG_PATH):
        os.remove(OUTPUT_CONFIG_PATH)

def test_apply_all_strategies_with_custom_configs(mock_modal):
    """ 
    Test que simula:
    1. Seleccionar todas las estrategias Forex y de Velas.
    2. Cargar todas las configuraciones 'Custom' para las velas.
    3. Aplicar los cambios.
    4. Verificar que el archivo 'strategies.json' se genera correctamente.
    """
    modal = mock_modal

    # --- 1. Simular acciones del usuario ---
    # Seleccionar todo en ambas pestañas
    modal._select_all_forex()
    modal._select_all_candles()

    # Cargar todas las estrategias de velas (esto cambiará el modo a 'Custom' si existe un .json)
    modal._load_all_candle_strategies()

    # Aplicar y guardar la configuración
    modal._apply_and_run_simulation()

    # --- 2. Verificar el resultado ---
    # Comprobar que el archivo de configuración fue creado
    assert os.path.exists(OUTPUT_CONFIG_PATH), "El archivo 'strategies.json' no fue creado."

    # Cargar y validar el contenido del archivo JSON
    with open(OUTPUT_CONFIG_PATH, 'r') as f:
        saved_config = json.load(f)

    # --- Verificaciones para Estrategias Forex ---
    assert 'forex_strategies' in saved_config
    forex_strategies = saved_config['forex_strategies']
    assert len(forex_strategies) > 0, "No se guardaron estrategias Forex."
    for name, config in forex_strategies.items():
        assert config['selected'] is True
        assert config['percent_ratio'] == 1.0
        assert config['rr_ratio'] == 2.0
        assert config['stop_loss_pips'] == 20.0

    # --- Verificaciones para Estrategias de Velas ---
    assert 'candle_strategies' in saved_config
    candle_strategies = saved_config['candle_strategies']
    assert len(candle_strategies) > 0, "No se guardaron estrategias de velas."

    for name, config in candle_strategies.items():
        assert config['selected'] is True
        
        # Si el modo es 'Custom', verificar que la configuración se cargó
        if config['strategy_mode'] == 'Custom':
            assert 'config' in config and config['config'], f"La configuración detallada para '{name}' no se cargó."
            
            # Cargar el archivo JSON original para comparar
            original_config_path = os.path.join(STRATEGIES_DIR, f"{name.replace('is_', '')}.json")
            assert os.path.exists(original_config_path)
            with open(original_config_path, 'r') as f_orig:
                original_config = json.load(f_orig)
            
            assert config['config'] == original_config, f"La configuración para '{name}' no coincide con el archivo original."
        else: # Modo 'Default'
            assert 'config' in config and not config['config'], f"La configuración para '{name}' no debería tener detalles en modo Default."

    print("\nTest completado con éxito: 'strategies.json' se generó correctamente.")

def test_initialization(mock_modal):
    pass
