# bluebikes-busiest-day-2024
Visualizing the Busiest Day of 2024 for Blue Bikes in Boston


##Setup

### Prerequisites  
- **uv**

### Setup  
```bash
git clone https://…/bluebikes-busiest-day.git
cd bluebikes-busiest-day

# Initialize uv in this directory
uv init .

# Add project dependencies
uv add pandas panel hvplot pyarrow

# (optional) Pin Python version
uv python pin 3.13

# Install all deps
uv sync
