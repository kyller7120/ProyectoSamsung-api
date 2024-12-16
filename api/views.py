import os, json, requests
from django.conf import settings
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet

class TeamViewSet(ViewSet):
    """
    ViewSet para manejar solicitudes relacionadas con equipos | samsung-devs.
    """
    def list(self, request):
        """
        Maneja solicitudes GET en /teams/
        """
        team_name = request.query_params.get('team_name', '').strip()
        if not team_name:
            return Response({"error": "El parámetro 'team_name' es requerido."}, status=400)

        # Definir nombre del archivo basándonos en el nombre del equipo
        file_name = f"team_{team_name}.json"
        file_path = os.path.join('data', 'teams', file_name)

        # Verificar si el archivo ya existe
        if os.path.exists(file_path):
            # Leer datos desde el archivo JSON
            with open(file_path, 'r') as file:
                data = json.load(file)
            filtered_clubs = [
                club for club in data.get('clubs', []) if club['competitionName'] == 'LaLiga'
            ]
            if not filtered_clubs:
                return Response({"message": "Este equipo no forma parte de LaLiga."}, status=404)
            return Response(filtered_clubs)

        # Si el archivo no existe, hacer la solicitud a la API
        url = "https://transfermarket.p.rapidapi.com/search"
        headers = {
            'x-rapidapi-key': getattr(settings, 'RAPIDAPI_KEY', None),
            'x-rapidapi-host': getattr(settings, 'RAPIDAPI_HOST', None)
        }
        querystring = {"query": team_name, "domain": "de"}

        try:
            response = requests.get(url, headers=headers, params=querystring)
            response.raise_for_status()
            
            data = response.json()
            filtered_clubs = [
                club for club in data.get('clubs', []) if club['competitionName'] == 'LaLiga'
            ]
            
            if not filtered_clubs:
                return Response({"message": "Este equipo no forma parte de LaLiga."}, status=404)
            
            # Guardar los datos en un archivo JSON
            self._save_json(data, 'teams', file_name)
            
            return Response(filtered_clubs)
        
        except requests.exceptions.RequestException as e:
            return Response({"error": f"Error al obtener datos: {str(e)}"}, status=502)

    def _save_json(self, data, folder, file_name):
        """
        Guarda los datos obtenidos en un archivo JSON dentro de una carpeta específica.
        """
        directory = os.path.join('data', folder)
        os.makedirs(directory, exist_ok=True)
        file_path = os.path.join(directory, file_name)

        with open(file_path, 'w') as json_file:
            json.dump(data, json_file, indent=4)


class PlayersViewSet(ViewSet):
    """
    ViewSet para manejar solicitudes relacionadas con jugadores de un equipo en una temporada dada.
    """
    def list(self, request):
        """
        Maneja solicitudes GET en /players/
        Obtiene los jugadores de un equipo para una temporada específica.
        """
        team_id = request.query_params.get('team_id', '').strip()
        if not team_id:
            return Response({"error": "El parámetro 'team_id' es requerido."}, status=400)

        season_id = request.query_params.get('season_year', '')
        if not season_id:
            return Response({"error": "El año de la temporada es obligatorio."}, status=400)

        # Definir nombre del archivo basándonos en el equipo y temporada
        file_name = f"players_{team_id}_{season_id}.json"
        file_path = os.path.join('data', 'players', file_name)

        # Verificar si el archivo ya existe
        if os.path.exists(file_path):
            # Leer datos desde el archivo JSON
            with open(file_path, 'r') as file:
                data = json.load(file)
            players_with_id = self._process_players(data)
            return Response({
                'team_id': team_id,
                'season_year': season_id,
                'players': players_with_id,
            })

        # Si el archivo no existe, hacer la solicitud a la API
        url = "https://transfermarket.p.rapidapi.com/clubs/get-squad"
        headers = {
            'x-rapidapi-key': getattr(settings, 'RAPIDAPI_KEY', None),
            'x-rapidapi-host': getattr(settings, 'RAPIDAPI_HOST', None)
        }
        querystring = {
            "id": team_id,
            "saison_id": season_id,
            "domain": "de"
        }

        try:
            response = requests.get(url, headers=headers, params=querystring)
            response.raise_for_status()

            data = response.json()
            players_with_id = self._process_players(data)

            # Guardar los datos en un archivo JSON
            self._save_json(data, 'players', file_name)
            
            return Response({
                'team_id': team_id,
                'season_year': season_id,
                'players': players_with_id,
            })
        
        except requests.exceptions.RequestException as e:
            return Response({"error": f"Error al obtener los jugadores: {str(e)}"}, status=502)

    def _process_players(self, data):
        """
        Procesa la lista de jugadores y genera un diccionario con su información.
        """
        players_with_id = {}
        for idx, player in enumerate(data.get('squad', [])):
            if 'name' in player and 'id' in player:
                simulated_id = idx + 1
                players_with_id[simulated_id] = {
                    'player_id': player['id'],
                    'name': player['name'],
                    'position': player['positions'].get('first', {}).get('name', 'Unknown'),
                    'marketValue': player.get('marketValue', {}).get('value', 'N/A'),
                    'currency': player.get('marketValue', {}).get('currency', 'Unknown')
                }
        return players_with_id

    def _save_json(self, data, folder, file_name):
        """
        Guarda los datos obtenidos en un archivo JSON dentro de una carpeta específica.
        """
        directory = os.path.join('data', folder)
        os.makedirs(directory, exist_ok=True)
        file_path = os.path.join(directory, file_name)

        with open(file_path, 'w') as json_file:
            json.dump(data, json_file, indent=4)

class PlayerViewSet(ViewSet):
    """
    ViewSet para manejar solicitudes relacionadas con la información de un jugador específico en múltiples temporadas.
    """
    API_HEADERS = {
        'x-rapidapi-key': getattr(settings, 'RAPIDAPI_KEY', None),
        'x-rapidapi-host': getattr(settings, 'RAPIDAPI_HOST', None)
    }
    SQUAD_URL = "https://transfermarket.p.rapidapi.com/clubs/get-squad"
    PERFORMANCE_URL = "https://transfermarket.p.rapidapi.com/players/get-performance-detail"

    def _save_json(self, data, file_path):
        """
        Guarda los datos en un archivo JSON.
        """
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=4)

    def _load_json(self, file_path):
        """
        Carga los datos desde un archivo JSON.
        """
        if os.path.exists(file_path):
            with open(file_path, 'r') as f:
                return json.load(f)
        return None

    def retrieve(self, request, pk=None):
        """
        Maneja solicitudes GET en /players/<player_id>/.
        Itera sobre temporadas entre 2024 y 2017 para obtener datos de desempeño.
        """
        required_params = ['team_id', 'season_year']
        missing_params = [param for param in required_params if not request.query_params.get(param, '').strip()]
        if missing_params:
            return Response({"error": f"Faltan parámetros obligatorios: {', '.join(missing_params)}."}, status=400)

        team_id = request.query_params['team_id']
        season_year = request.query_params['season_year']
        competitionID = "ES1"
        
        # Verificar si ya existe el archivo JSON para este jugador, temporada y equipo
        player_file_path = f'data/player/{team_id}_{pk}_{season_year}.json' 
        player_data = self._load_json(player_file_path)

        if player_data:
            # Si el archivo existe, se devuelve directamente desde el archivo
            return Response(player_data)

        # Si no existe el archivo, obtener los datos desde la API
        try:
            squad_response = self._fetch_data(self.SQUAD_URL, params={"id": team_id, "saison_id": season_year, "domain": "de"})
        except requests.exceptions.RequestException as e:
            return Response({"error": f"Error al obtener la lista del equipo: {str(e)}"}, status=502)

        player = next((p for p in squad_response.get('squad', []) if str(p.get('id')) == str(pk)), None)
        if not player:
            return Response({"message": "No se encontró un jugador con este ID."}, status=404)

        # Inicializar variables para estadísticas acumuladas
        estadisticas_por_temporada = {}
        total_goles = 0
        total_asistencias = 0
        total_goles_en_propia = 0
        total_tarjetas_amarillas = 0
        total_tarjetas_rojas = 0
        total_tarjetas_rojasamarillas = 0

        # Iterar sobre las temporadas desde 2024 hasta 2015
        for season_yeaar in range(2024, 2016, -1):
            player_season_file_path = f'data/player/{team_id}_{pk}_{season_year}.json'

            # Verificar si ya existe un archivo para esta temporada
            season_data = self._load_json(player_season_file_path)
            if season_data:
                estadisticas_por_temporada[season_year] = season_data
                total_goles += season_data['goles']
                total_asistencias += season_data['asistencias']
                total_goles_en_propia += season_data['goles_en_propia']
                total_tarjetas_amarillas += season_data['tarjetas_amarillas']
                total_tarjetas_rojas += season_data['tarjetas_rojas']
                total_tarjetas_rojasamarillas += season_data['tarjetas_rojasamarillas']
                continue

            # Si no existe, obtener los datos de la API
            try:
                performance_response = self._fetch_data(self.PERFORMANCE_URL, params={
                    "id": player['id'], "seasonID": season_yeaar, "competitionID": competitionID, "domain": "de"
                })
            except requests.exceptions.RequestException as e:
                return Response({"error": f"Error al obtener el desempeño del jugador para la temporada {season_yeaar}: {str(e)}"}, status=502)

            season_goles = 0
            season_asistencias = 0
            season_goles_en_propia = 0
            season_tarjetas_amarillas = 0
            season_tarjetas_rojas = 0
            season_tarjetas_rojasamarillas = 0
            team_name = 'No participó en el equipo'

            if 'matchPerformance' in performance_response:
                for match in performance_response['matchPerformance']:
                    if 'match' in match:
                        info = match['match']
                        if(('homeTeam' in info) and ('awayTeam' in info)):
                            home = info['homeTeam']
                            away = info['awayTeam']

                            idHome = int(home.get('id') or 0)
                            nameHome = str(home.get('name') or 'Unknown')
                            idAway = int(away.get('id') or 0)
                            nameAway = str(away.get('name') or 'Unknown')
                            team_name = nameAway
                            if(idHome == int(team_id)):
                                team_name = nameHome

                    if 'performance' in match:
                        perf = match['performance']
                        season_goles += int(perf.get('goals', 0) or 0)
                        season_asistencias += int(perf.get('assists', 0) or 0)
                        season_goles_en_propia += int(perf.get('ownGoals', 0) or 0)
                        season_tarjetas_amarillas += 1 if perf.get('yellowCardMinute') not in [None, "0"] else 0
                        season_tarjetas_rojas += 1 if perf.get('redCardMinute') not in [None, "0"] else 0
                        season_tarjetas_rojasamarillas += 1 if perf.get('yellowRedCardMinute') not in [None, "0"] else 0

            season_data = {
                'goles': season_goles,
                'asistencias': season_asistencias,
                'goles_en_propia': season_goles_en_propia,
                'tarjetas_amarillas': season_tarjetas_amarillas,
                'tarjetas_rojas': season_tarjetas_rojas,
                'tarjetas_rojasamarillas': season_tarjetas_rojasamarillas,
                'team_name': team_name,
            }

            estadisticas_por_temporada[season_yeaar] = season_data
            total_goles += season_goles
            total_asistencias += season_asistencias
            total_goles_en_propia += season_goles_en_propia
            total_tarjetas_amarillas += season_tarjetas_amarillas
            total_tarjetas_rojas += season_tarjetas_rojas
            total_tarjetas_rojasamarillas += season_tarjetas_rojasamarillas


        # Guardar todos los datos del jugador en un solo archivo JSON
        player_data = {
            "estadisticas": {
                'player_id': player['id'],
                'name': player['name'],
                'position': player['positions'].get('first', {}).get('name', 'Unknown'),
                'marketValue': player.get('marketValue', {}).get('value', 'N/A'),
                'currency': player.get('marketValue', {}).get('currency', 'Unknown'),
                'age': player.get('age', 'Unknown'),
                'height': player.get('height'),
                'weight': 'Unknown',
                "goles": total_goles,
                "asistencias": total_asistencias,
                "goles_en_propia": total_goles_en_propia,
                "tarjetas_amarillas": total_tarjetas_amarillas,
                "tarjetas_rojas": total_tarjetas_rojas,
                "tarjetas_rojasamarillas": total_tarjetas_rojasamarillas
            },
            "estadisticas_por_temporada": estadisticas_por_temporada
        }

        # Guardar todos los datos del jugador en el archivo
        self._save_json(player_data, player_file_path)

        return Response(player_data)

    def _fetch_data(self, url, params):
        """
        Función auxiliar para realizar solicitudes y manejar respuestas.
        """
        response = requests.get(url, headers=self.API_HEADERS, params=params)
        response.raise_for_status()
        return response.json()


class PlayerValueMarketViewSet(ViewSet):
    """
    ViewSet para manejar solicitudes relacionadas con el historial de mercado de un jugador específico.
    """
    API_HEADERS = {
        'x-rapidapi-key': getattr(settings, 'RAPIDAPI_KEY', None),
        'x-rapidapi-host': getattr(settings, 'RAPIDAPI_HOST', None)
    }
    HISTORY_URL = "https://transfermarket.p.rapidapi.com/players/get-market-value"

    def _save_json(self, data, file_path):
        """
        Guarda los datos en un archivo JSON.
        """
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=4)

    def _load_json(self, file_path):
        """
        Carga los datos desde un archivo JSON.
        """
        if os.path.exists(file_path):
            with open(file_path, 'r') as f:
                return json.load(f)
        return None

    def list(self, request):
        """
        Devuelve la información acerca del historial de mercado de un jugador específico.
        """
        # Verificar si el parámetro obligatorio player_id está presente
        player_id = request.query_params.get('player_id', '').strip()
        if not player_id:
            return Response({"error": "El parámetro 'player_id' es obligatorio."}, status=400)

        # Verificar si ya existe el archivo JSON para este jugador
        player_history_file_path = f'data/player-history/{player_id}.json'
        player_history_data = self._load_json(player_history_file_path)

        if player_history_data:
            # Si el archivo existe, devolver directamente desde el archivo
            return Response(player_history_data)

        # Si no existe el archivo, obtener los datos desde la API
        try:
            player_history_response = self._fetch_data(self.HISTORY_URL, params={"id": player_id, "domain": "de"})
            # Verificar la respuesta para asegurarse de que contiene la clave 'marketValueDevelopment'
            if 'marketValueDevelopment' not in player_history_response:
                return Response({"error": "No se encontraron datos de desarrollo del valor de mercado."}, status=404)
            
            player_history_data = player_history_response['marketValueDevelopment']
        except requests.exceptions.RequestException as e:
            return Response({"error": f"Error al obtener la información del jugador: {str(e)}"}, status=502)

        # Filtrar solo los campos necesarios
        filtered_data = []
        for entry in player_history_data:
            filtered_data.append({
                'age': entry.get('age'),
                'marketValueUnformatted': entry.get('marketValueUnformatted'),
                'marketValueCurrency': entry.get('marketValueCurrency'),
                'clubName': entry.get('clubName'),
                'clubImage': entry.get('clubImage'),
                'seasonID': entry.get('seasonID'),
            })

        # Guardar los datos filtrados en un archivo JSON
        self._save_json(filtered_data, player_history_file_path)

        return Response(filtered_data)

    def _fetch_data(self, url, params):
        """
        Función auxiliar para realizar solicitudes y manejar respuestas.
        """
        response = requests.get(url, headers=self.API_HEADERS, params=params)
        response.raise_for_status()
        return response.json()
