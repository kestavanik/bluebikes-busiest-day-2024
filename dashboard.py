import panel as pn
import pandas as pd
import param
import numpy as np
from src.data_loader import load_and_prepare_visualization_data, filter_data_for_time_window

pn.extension('deckgl', design='bootstrap', theme='dark', template='bootstrap')

pn.state.template.config.raw_css.append("""
#main {
  padding: 0;
}""")

class App(pn.viewable.Viewer):
    start_data = param.DataFrame(precedence=-1)
    end_data = param.DataFrame(precedence=-1)
    view_start = param.DataFrame(precedence=-1)
    view_end = param.DataFrame(precedence=-1)
    
    # Remove radius and bike_type from parameters
    time_window = param.Integer(default=0, bounds=(0, 143))
    speed = param.Integer(default=1, bounds=(1, 10), label="Animation Speed")
    play = param.Event(label='▷')
    
    # Hardcode the radius
    HEXAGON_RADIUS = 50
    
    # Global elevation scaling based on entire 24-hour dataset
    global_max_start_events = param.Integer(default=1, precedence=-1)
    global_max_end_events = param.Integer(default=1, precedence=-1)
    
    GREEN_COLOR_RANGE = [
        [229,245,224,255],[199,233,192,255],[161,217,155,255],
        [116,196,118,255],[65,171,93,255],[35,139,69,255]
    ]
    RED_COLOR_RANGE = [
        [254,229,217,255],[252,187,161,255],[252,146,114,255],
        [251,106,74,255],[239,59,44,255],[203,24,29,255],[165,15,21,255]
    ]
    
    def __init__(self, start_data, end_data, **params):
        self.deck_gl = None
        super().__init__(**params)
        
        self.start_data = start_data
        self.end_data = end_data
        self.view_start = pd.DataFrame()
        self.view_end = pd.DataFrame()
        
        # Calculate global maximums for relative elevation scaling
        self._calculate_global_elevation_scale()
        
        self._update_time_window_view()
        
        self.deck_gl = pn.pane.DeckGL(
            self.spec,
            sizing_mode='stretch_both',
            margin=0        )
        
        self._playing = False
        self._cb = pn.state.add_periodic_callback(
            self._update_time_window, 1000//max(1, self.speed), start=False
        )

    def _calculate_global_elevation_scale(self):
        """
        Calculate the maximum number of events per coordinate group across all time windows.
        This ensures hexagon elevations are relative to the entire 24-hour dataset.
        """
        if len(self.start_data) == 0 or len(self.end_data) == 0:
            return
            
        # For start events: group by coordinate group and time window, count events
        start_grouped = (self.start_data.groupby(['coordinate_group_id', 'time_window'])
                        .size()
                        .reset_index(name='event_count'))
        
        # For end events: group by coordinate group and time window, count events  
        end_grouped = (self.end_data.groupby(['coordinate_group_id', 'time_window'])
                      .size()
                      .reset_index(name='event_count'))
        
        # Find the maximum events per coordinate group in any single time window
        self.global_max_start_events = start_grouped['event_count'].max() if len(start_grouped) > 0 else 1
        self.global_max_end_events = end_grouped['event_count'].max() if len(end_grouped) > 0 else 1
        
        print(f"Global elevation scaling calculated:")
        print(f"  Max start events per coordinate group: {self.global_max_start_events}")
        print(f"  Max end events per coordinate group: {self.global_max_end_events}")

    @property
    def start_hex_layer(self):
        data = self.view_start
        
        if len(data) > 0:
            local_max = data.groupby('coordinate_group_id').size().max()
        else:
            local_max = 1

        scale_factor = (local_max / self.global_max_start_events) if self.global_max_start_events else 1
        elevation_scale = 20 * scale_factor

        return {
            "@@type": "HexagonLayer",
            "id": "start-hexagon-layer",
            "data": data if len(data) > 0 else [],
            "pickable": False,
            "coverage": 1,
            "elevationRange": [0, 100],
            "elevationScale": elevation_scale,
            "radius": self.HEXAGON_RADIUS,
            "extruded": True,
            "getPosition": "@@=[group_lng, group_lat]",
            "colorRange": self.GREEN_COLOR_RANGE
        }

    @property
    def end_hex_layer(self):
        data = self.view_end

        if len(data) > 0:
            local_max = data.groupby('coordinate_group_id').size().max()
        else:
            local_max = 1

        scale_factor = (local_max / self.global_max_end_events) if self.global_max_end_events else 1
        elevation_scale = 20 * scale_factor

        return {
            "@@type": "HexagonLayer",
            "id": "end-hexagon-layer",
            "data": data if len(data) > 0 else [],
            "pickable": False,
            "coverage": 1,
            "elevationRange": [0, 100],
            "elevationScale": elevation_scale,
            "radius": self.HEXAGON_RADIUS,
            "extruded": True,
            "getPosition": "@@=[group_lng, group_lat]",
            "colorRange": self.RED_COLOR_RANGE
        }

    def format_time(self, value):
        """Helper to turn time_window index into H:MM AM/PM"""
        hours_24 = (value * 10) // 60
        minutes = (value * 10) % 60
        period = "AM" if hours_24 < 12 else "PM"
        hours_12 = hours_24 % 12 or 12
        return f"{hours_12}:{minutes:02d} {period}"
        
    @param.depends('view_start', 'view_end', 'time_window')
    def spec(self):
        return {
            "initialViewState": {
                "bearing": 0,
                "latitude": 42.35,
                "longitude": -71.09,
                "maxZoom": 15,
                "minZoom": 5,
                "pitch": 40.5,
                "zoom": 13.5
            },            "mapStyle": "https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json",
            "layers": [self.start_hex_layer, self.end_hex_layer],
            "views": [
                {"@@type": "MapView", "controller": True}
            ]
        }

    def _update_time_window(self):
        self.time_window = (self.time_window + 1) % 144

    @param.depends('time_window', watch=True)
    def _update_time_window_view(self):
        if len(self.start_data) == 0 or len(self.end_data) == 0:
            return
            
        self.view_start, self.view_end = filter_data_for_time_window(
            self.start_data, self.end_data, self.time_window, 'all'  # Always use 'all'
        )

    @param.depends('speed', watch=True)
    def _update_speed(self):
        if self._cb and self.speed > 0:
            self._cb.period = 1000//max(1, self.speed)

    @param.depends('play', watch=True)
    def _play_pause(self):
        if self._playing:
            self._cb.stop()
            self.param.play.label = '⏵'
            # Removed speed precedence change
        else:
            self._cb.start()
            self.param.play.label = '⏸'
            # Removed speed precedence change
        self._playing = not self._playing

    @property
    def controls(self):
        def time_formatter(value):
            hours_24 = (value * 10) // 60
            minutes = (value * 10) % 60
            period = "AM" if hours_24 < 12 else "PM"
            hours_12 = hours_24 % 12
            if hours_12 == 0:
                hours_12 = 12
            return f"{hours_12}:{minutes:02d} {period}"

        def time_range_formatter(value):
            start = value
            end = (value + 1) % 144
            return f"{time_formatter(start)} – {time_formatter(end)}"

        time_window_slider = pn.widgets.IntSlider.from_param(
            self.param.time_window, 
            name="",  # Completely empty string
            show_value=False,
            tooltips=True
        )
        time_display = pn.widgets.StaticText(name='Current Window', value=time_range_formatter(self.time_window))
        total_events_display = pn.widgets.StaticText(name='Total Events', value="0")
        start_events_display = pn.widgets.StaticText(name='Pickups', value="0")
        end_events_display = pn.widgets.StaticText(name='Dropoffs', value="0")
        
        @pn.depends(time_window=self.param.time_window)
        def update_time_display(time_window):
            time_display.value = time_range_formatter(time_window)
            start_count = len(self.view_start) if self.view_start is not None else 0
            end_count = len(self.view_end) if self.view_end is not None else 0
            total_events_display.value = str(start_count + end_count)
            start_events_display.value = str(start_count)
            end_events_display.value = str(end_count)
            return ""
        
        controls = pn.Column(
            pn.pane.Markdown("### About This Visualization", margin=(0,0,10,0)),
            pn.pane.Markdown("""
            This visualization shows Blue Bikes activity in Boston on September 17, 2024, 
            which was determined to be the busiest day in 2024 based on total rides.
            
            **Green Hexagons** - Blue Bike start locations 
            \n
            **Red Hexagons** - Blue Bike end locations
    
            Hexagonal bins group nearby stations to show overall activity patterns, the higher the hexagon's elevation,
            the more start or end events in that area.
            \n
            The time slider allows you to explore activity in 10-minute intervals throughout the day.  
            """, margin=(0,0,20,0)),
            time_window_slider,
            pn.Row(time_display),
            pn.Row(
                start_events_display, 
                end_events_display, 
                total_events_display,
                margin=(0,0,10,0)
            ),
            update_time_display,
            pn.Row(
                pn.Param(
                    self.param, 
                    parameters=['play', 'speed'],
                    widgets={
                        'play': {
                            'type': pn.widgets.Button, 
                            'width': 50, 
                            'css_classes': ['bk-btn-play'],
                            'align': 'center'
                        },
                        'speed': {
                            'type': pn.widgets.IntSlider, 
                            'width': 150, 
                            'name': 'Speed',
                            'margin': (5,0,0,10)  # Add left margin for spacing
                        },
                    },
                    show_name=False,
                    default_layout=pn.Row,
                    margin=0
                ),
                align='center',
                margin=(10,0,0,0)
            ),
            margin=(20,10),
            css_classes=['control-panel'],
            height=800,
            sizing_mode='stretch_width'
        )
        
        # Update play button class based on state
        if self._playing:
            controls.select(pn.widgets.Button).css_classes = ['bk-btn-pause']
        
        return controls

    def __panel__(self):
        return pn.Row(
            self.controls,
            self.deck_gl,
            min_height=800,
            sizing_mode='stretch_both',
        )

try:
    full_data, start_data, end_data = load_and_prepare_visualization_data(
        'data/processed/bluebikes_events.parquet',
        group_coordinates=True,
        distance_threshold_meters=30.0
    )
    
    app = App(start_data=start_data, end_data=end_data)
    
    app.controls.servable(area='sidebar')
    app.deck_gl.servable(title='Blue Bikes Buisiest Day of 2024 in Boston')
    
except Exception as e:
    error_pane = pn.pane.Markdown(f"""
    # Error Loading Dashboard
    
    There was an error loading the dashboard: {str(e)}
    
    Please check that the data file exists and is in the correct format.
    """)
    error_pane.servable()