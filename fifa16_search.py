#!/usr/bin/env python3
"""
Motor de busca de jogadores do FIFA 16, construído sobre o parser
existente (fifa16_db_parser.py).

Combina dois bancos de dados:
    1. Banco ESTÁTICO do jogo (fifa_ng_db.db) — nomes de jogadores
       (tabela BGwe: nameid -> name) e nações (tabela Crbb:
       nationid -> nationname). Não muda entre saves.
    2. Banco do SAVE ativo (arquivo DATA dentro de uma pasta de save
       em Documents/FIFA 16/0/FIFA16/<hash>/DATA) — atributos e
       estado atual de cada jogador (tabela CZUM), já que overall,
       potential etc. podem ter sido alterados pelo usuário na
       carreira.

Uso como CLI (retorna JSON no stdout):

    python fifa16_search.py --position ST --min-overall 75 --min-potential 85

Uso como biblioteca:

    from fifa16_search import FifaDatabase
    db = FifaDatabase.auto_load()
    results = db.search_players(position="ST", min_overall=75)
"""

from __future__ import annotations

import argparse
import io
import json
import sys
import unicodedata
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path

import fifa16_db_parser as parser


def normalize_text(text: str) -> str:
    """Remove acentos e normaliza para minúsculas, para busca tolerante
    (ex: 'mbappe' deve casar com 'Mbappé')."""
    normalized = unicodedata.normalize("NFKD", text)
    without_accents = "".join(c for c in normalized if not unicodedata.combining(c))
    return without_accents.lower()

# Força stdout/stderr em UTF-8 independente do codepage do console do
# Windows — necessário porque nomes de jogadores contêm acentos e
# outros caracteres não-ASCII (ex: "Mbappé"), e o codepage padrão do
# console (cp1252/cp850) não os suporta, causando corrupção quando a
# saída é capturada por outro processo (ex: Electron via subprocess).
if sys.stdout.encoding is None or sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
if sys.stderr.encoding is None or sys.stderr.encoding.lower() != "utf-8":
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# ----------------------------------------------------------------------
# Configuração de caminhos padrão (Windows / instalação típica)
# ----------------------------------------------------------------------

DEFAULT_SAVES_DIR = Path.home() / "Documents" / "FIFA 16" / "0" / "FIFA16"
DEFAULT_STATIC_DB = Path("D:/Program Files/FIFA 16/data/db/fifa_ng_db.db")
DEFAULT_METADATA = Path("D:/Program Files/FIFA 16/data/db/fifa_ng_db-meta.xml")

CONFIG_PATH = Path(__file__).parent / "fifa16_search_config.json"

# Enum de posições do FIFA 16 (conhecido da comunidade de modding).
# Cobre os valores 0-27 observados nos dados (15 não é usado).
POSITION_NAMES = {
    0: "GK",
    1: "RWB", 2: "RB", 3: "RCB", 4: "CB", 5: "LCB", 6: "LB", 7: "LWB",
    8: "RDM", 9: "CDM", 10: "LDM",
    11: "RM", 12: "RCM", 13: "CM", 14: "LCM", 15: "LM",
    16: "RAM", 17: "CAM", 18: "LAM",
    19: "RF", 20: "CF", 21: "LF",
    22: "RW", 23: "RS", 24: "ST", 25: "LS", 26: "LW",
    27: "SUB",
}

# Mapa inverso (nome -> lista de códigos), para permitir buscar por
# "ST" e casar com qualquer variação (RS/ST/LS costumam ser tratadas
# como "atacante central" na comunidade, mas aqui mantemos 1:1 fiel
# ao enum; buscas por nome curto tipo "CB" casam várias variações via
# POSITION_GROUPS abaixo).
POSITION_GROUPS = {
    "GK": [0],
    "CB": [3, 4, 5],
    "RB": [1, 2],
    "LB": [6, 7],
    "CDM": [8, 9, 10],
    "CM": [12, 13, 14],
    "RM": [11],
    "LM": [15],
    "CAM": [16, 17, 18],
    "RW": [22],
    "LW": [26],
    "ST": [19, 20, 21, 23, 24, 25],
}


def resolve_position_codes(position: str) -> list[int]:
    position = position.upper().strip()
    if position in POSITION_GROUPS:
        return POSITION_GROUPS[position]
    # tenta achar por nome exato no enum (ex.: "LCM", "RCB")
    codes = [code for code, name in POSITION_NAMES.items() if name == position]
    return codes


# Data de referência usada pelo FIFA para o campo `birthdate` (dias
# desde essa época). Validado empiricamente comparando as datas de
# nascimento reais de Kylian Mbappé (1998-12-20) e Erling Haaland
# (2000-07-21) com os valores brutos de birthdate no save
# (152008 e 152587 respectivamente): a diferença em dias entre as
# duas datas reais (579) bate exatamente com a diferença dos valores
# brutos (579), confirmando que a unidade é "dias". Resolvendo a
# época a partir de qualquer um dos dois dá 1582-10-14 (dia seguinte
# à reforma do calendário Gregoriano — uma época de referência comum
# em alguns formatos de data numérica/ordinal).
FIFA_DATE_EPOCH = date(1582, 10, 14)


def decode_yyyymmdd(raw_value: int) -> date | None:
    """
    Decodifica um inteiro no formato YYYYMMDD (ex: 20351102 ->
    2035-11-02). Usado para o campo `currdate` da tabela GJUr, que
    representa a data ATUAL da carreira em andamento — diferente de
    `birthdate` dos jogadores, que usa dias desde FIFA_DATE_EPOCH.
    """
    if not raw_value or raw_value < 10000101:
        return None
    year = raw_value // 10000
    month = (raw_value // 100) % 100
    day = raw_value % 100
    try:
        return date(year, month, day)
    except ValueError:
        return None


def compute_age(birthdate_value: int, as_of: date | None = None) -> int | None:
    """
    Calcula a idade a partir do campo birthdate bruto (dias desde
    FIFA_DATE_EPOCH).

    `as_of` é a data de referência para o cálculo — deve ser a data
    ATUAL DA CARREIRA (campo `currdate` da tabela GJUr), não a data
    real do sistema. Isso é importante porque carreiras podem estar
    ambientadas em anos bem diferentes do ano real (ex: um save pode
    estar em 2035), e usar a data real do PC produziria idades
    completamente erradas para jogadores "regen" (gerados durante a
    carreira, com datas de nascimento recentes em termos absolutos
    mas que já são adultos dentro da linha do tempo do save).
    """
    if not birthdate_value:
        return None

    try:
        birth = FIFA_DATE_EPOCH + timedelta(days=birthdate_value)
    except OverflowError:
        return None

    if as_of is None:
        # sem data de carreira disponível — não arriscamos calcular
        # com a data real do sistema, que provavelmente estaria
        # errada por vários anos.
        return None

    reference = as_of

    age = reference.year - birth.year
    if (reference.month, reference.day) < (birth.month, birth.day):
        age -= 1

    return age


@dataclass
class PlayerRecord:
    player_id: int
    first_name: str
    last_name: str
    overall: int
    potential: int
    position_code: int
    position_name: str
    nationality_id: int
    nationality_name: str
    preferred_foot: int
    height: int
    weight: int
    age: int | None = None

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()

    def to_dict(self) -> dict:
        return {
            "player_id": self.player_id,
            "name": self.full_name,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "overall": self.overall,
            "potential": self.potential,
            "position": self.position_name,
            "position_code": self.position_code,
            "nationality": self.nationality_name,
            "nationality_id": self.nationality_id,
            # Convenção do FIFA: 1 = Right, 2 = Left. Confirmado pelo
            # range do campo no metadata XML (rangelow=1, rangehigh=2)
            # e validado cruzando com jogadores reais conhecidos:
            # Mbappé (destro) = 1, Haaland (canhoto) = 2.
            "preferred_foot": "Left" if self.preferred_foot == 2 else "Right",
            "height": self.height,
            "weight": self.weight,
            "age": self.age,
        }


class FifaDatabase:
    """
    Carrega e indexa os dados necessários para busca de jogadores.
    """

    def __init__(self, players: list[PlayerRecord]):
        self.players = players

    # ------------------------------------------------------------------
    # Carregamento
    # ------------------------------------------------------------------

    @staticmethod
    def find_save_dirs(saves_root: Path = DEFAULT_SAVES_DIR) -> list[Path]:
        """
        Lista pastas de save candidatas (contêm DATA + INDEX),
        ordenadas da mais recente para a mais antiga por mtime do
        arquivo DATA. Ignora saves muito pequenos (<1MB), que
        parecem ser saves parciais/incompletos (ex.: staging).
        """

        if not saves_root.exists():
            return []

        candidates = []
        for entry in saves_root.iterdir():
            data_file = entry / "DATA"
            if data_file.exists() and data_file.stat().st_size > 1_000_000:
                candidates.append((data_file.stat().st_mtime, entry))

        candidates.sort(reverse=True)
        return [entry for _, entry in candidates]

    @classmethod
    def identify_saves(
        cls, metadata_path: Path = DEFAULT_METADATA
    ) -> list[dict]:
        """
        Lista todos os saves disponíveis com informações que ajudam a
        identificar qual é qual: nome do técnico/manager (tabela
        mPrV), data atual da carreira (tabela GJUr, formato YYYYMMDD)
        e data de modificação do arquivo. Não carrega jogadores —
        muito mais rápido que `auto_load` para esse propósito.
        """
        metadata = parser.load_metadata(metadata_path) if metadata_path.exists() else ({}, {}, {})

        results = []
        for save_dir in cls.find_save_dirs():
            data_path = save_dir / "DATA"
            raw = data_path.read_bytes()
            offsets = parser.find_databases(raw)

            manager_name = None
            career_date_raw = None

            for off in offsets:
                db = parser.parse_database(raw, off, metadata)
                for table in db["tables"]:
                    if table.short_name == "mPrV" and manager_name is None:
                        rows = parser.decode_table(raw, table)
                        if rows:
                            manager_name = (
                                f"{rows[0].get('firstname', '')} "
                                f"{rows[0].get('surname', '')}"
                            ).strip()
                    elif table.short_name == "GJUr" and career_date_raw is None:
                        rows = parser.decode_table(raw, table)
                        if rows:
                            career_date_raw = rows[0].get("currdate")

            career_date = decode_yyyymmdd(career_date_raw) if career_date_raw else None

            results.append(
                {
                    "save_dir": str(save_dir),
                    "manager": manager_name,
                    "career_date": career_date.isoformat() if career_date else None,
                    "file_modified": datetime.fromtimestamp(
                        data_path.stat().st_mtime
                    ).isoformat(timespec="seconds"),
                }
            )

        return results

    @staticmethod
    def load_last_used_save() -> Path | None:
        if CONFIG_PATH.exists():
            try:
                cfg = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
                path = Path(cfg["save_dir"])
                if (path / "DATA").exists():
                    return path
            except Exception:
                pass
        return None

    @staticmethod
    def save_last_used_save(save_dir: Path) -> None:
        CONFIG_PATH.write_text(
            json.dumps({"save_dir": str(save_dir)}), encoding="utf-8"
        )

    @classmethod
    def auto_load(
        cls,
        save_dir: Path | None = None,
        static_db_path: Path = DEFAULT_STATIC_DB,
        metadata_path: Path = DEFAULT_METADATA,
    ) -> "FifaDatabase":
        """
        Carrega o banco estático + o save mais recente (ou o
        especificado / o último usado salvo em config).
        """

        if save_dir is None:
            save_dir = cls.load_last_used_save()

        if save_dir is None:
            candidates = cls.find_save_dirs()
            if not candidates:
                raise FileNotFoundError(
                    f"Nenhum save encontrado em {DEFAULT_SAVES_DIR}"
                )
            save_dir = candidates[0]

        cls.save_last_used_save(save_dir)

        return cls.load(save_dir / "DATA", static_db_path, metadata_path)

    @classmethod
    def load(
        cls,
        save_data_path: Path,
        static_db_path: Path = DEFAULT_STATIC_DB,
        metadata_path: Path = DEFAULT_METADATA,
    ) -> "FifaDatabase":
        metadata = parser.load_metadata(metadata_path) if metadata_path.exists() else ({}, {}, {})

        # --- banco estático: nomes e nações ---
        static_raw = Path(static_db_path).read_bytes()
        static_offsets = parser.find_databases(static_raw)

        name_index: dict[int, str] = {}
        nation_index: dict[int, str] = {}

        for off in static_offsets:
            db = parser.parse_database(static_raw, off, metadata)
            for table in db["tables"]:
                if table.short_name == "BGwe":
                    for row in parser.decode_table(static_raw, table):
                        name_index[row["nameid"]] = row["name"]
                elif table.short_name == "Crbb":
                    for row in parser.decode_table(static_raw, table):
                        nation_index[row["nationid"]] = row["nationname"]

        # --- save ativo: atributos dos jogadores ---
        save_raw = Path(save_data_path).read_bytes()
        save_offsets = parser.find_databases(save_raw)

        # Primeiro localiza a data ATUAL da carreira (tabela GJUr,
        # campo currdate, formato YYYYMMDD) — necessária para calcular
        # idade corretamente, já que carreiras podem estar ambientadas
        # em anos bem diferentes do ano real do sistema (ex: 2035).
        career_date: date | None = None
        for off in save_offsets:
            db = parser.parse_database(save_raw, off, metadata)
            for table in db["tables"]:
                if table.short_name == "GJUr":
                    for row in parser.decode_table(save_raw, table):
                        career_date = decode_yyyymmdd(row.get("currdate", 0))
                        break
                if career_date:
                    break
            if career_date:
                break

        players: list[PlayerRecord] = []

        for off in save_offsets:
            db = parser.parse_database(save_raw, off, metadata)
            for table in db["tables"]:
                if table.short_name != "CZUM":
                    continue
                for row in parser.decode_table(save_raw, table):
                    pos_code = row.get("preferredposition1", -1)
                    nat_id = row.get("nationality", -1)

                    players.append(
                        PlayerRecord(
                            player_id=row.get("playerid", -1),
                            first_name=name_index.get(row.get("firstnameid"), ""),
                            last_name=name_index.get(row.get("lastnameid"), ""),
                            overall=row.get("overallrating", 0),
                            potential=row.get("potential", 0),
                            position_code=pos_code,
                            position_name=POSITION_NAMES.get(pos_code, f"?({pos_code})"),
                            nationality_id=nat_id,
                            nationality_name=nation_index.get(nat_id, f"?({nat_id})"),
                            preferred_foot=row.get("preferredfoot", 1),
                            height=row.get("height", 0),
                            weight=row.get("weight", 0),
                            age=compute_age(row.get("birthdate", 0), as_of=career_date),
                        )
                    )

        return cls(players)

    # ------------------------------------------------------------------
    # Busca
    # ------------------------------------------------------------------

    def search_players(
        self,
        name: str | None = None,
        position: str | None = None,
        min_overall: int | None = None,
        max_overall: int | None = None,
        min_potential: int | None = None,
        max_potential: int | None = None,
        nationality: str | None = None,
        preferred_foot: str | None = None,
        min_age: int | None = None,
        max_age: int | None = None,
        limit: int = 200,
        sort_by: str = "potential",
        descending: bool = True,
    ) -> list[PlayerRecord]:
        results = self.players

        if name:
            needle = normalize_text(name)
            results = [p for p in results if needle in normalize_text(p.full_name)]

        if position:
            codes = resolve_position_codes(position)
            if codes:
                results = [p for p in results if p.position_code in codes]

        if min_overall is not None:
            results = [p for p in results if p.overall >= min_overall]
        if max_overall is not None:
            results = [p for p in results if p.overall <= max_overall]
        if min_potential is not None:
            results = [p for p in results if p.potential >= min_potential]
        if max_potential is not None:
            results = [p for p in results if p.potential <= max_potential]

        if nationality:
            needle = nationality.lower()
            results = [p for p in results if needle in p.nationality_name.lower()]

        if preferred_foot:
            # 1 = Right, 2 = Left (ver nota em PlayerRecord.to_dict)
            foot_code = 2 if preferred_foot.lower().startswith("l") else 1
            results = [p for p in results if p.preferred_foot == foot_code]

        if min_age is not None:
            results = [p for p in results if p.age is not None and p.age >= min_age]
        if max_age is not None:
            results = [p for p in results if p.age is not None and p.age <= max_age]

        results = sorted(
            results, key=lambda p: getattr(p, sort_by, 0), reverse=descending
        )

        return results[:limit]


# ----------------------------------------------------------------------
# CLI
# ----------------------------------------------------------------------

def main() -> None:
    ap = argparse.ArgumentParser(description="Busca de jogadores do FIFA 16")
    ap.add_argument("--save-dir", help="Caminho da pasta de save (contém DATA/INDEX)")
    ap.add_argument("--static-db", default=str(DEFAULT_STATIC_DB))
    ap.add_argument("--metadata", default=str(DEFAULT_METADATA))
    ap.add_argument("--name")
    ap.add_argument("--position")
    ap.add_argument("--min-overall", type=int)
    ap.add_argument("--max-overall", type=int)
    ap.add_argument("--min-potential", type=int)
    ap.add_argument("--max-potential", type=int)
    ap.add_argument("--nationality")
    ap.add_argument("--foot", choices=["left", "right"])
    ap.add_argument("--min-age", type=int)
    ap.add_argument("--max-age", type=int)
    ap.add_argument("--limit", type=int, default=200)
    ap.add_argument("--sort-by", default="potential")
    ap.add_argument("--list-saves", action="store_true", help="Lista saves disponíveis e sai")
    ap.add_argument(
        "--identify-saves",
        action="store_true",
        help="Lista saves com manager, data da carreira e data de modificação (para identificar qual é qual)",
    )

    args = ap.parse_args()

    if args.list_saves:
        saves = FifaDatabase.find_save_dirs()
        print(json.dumps([str(s) for s in saves], indent=2))
        return

    if args.identify_saves:
        info = FifaDatabase.identify_saves(Path(args.metadata))
        print(json.dumps(info, ensure_ascii=False, indent=2))
        return

    save_dir = Path(args.save_dir) if args.save_dir else None

    db = FifaDatabase.auto_load(
        save_dir=save_dir,
        static_db_path=Path(args.static_db),
        metadata_path=Path(args.metadata),
    )

    results = db.search_players(
        name=args.name,
        position=args.position,
        min_overall=args.min_overall,
        max_overall=args.max_overall,
        min_potential=args.min_potential,
        max_potential=args.max_potential,
        nationality=args.nationality,
        preferred_foot=args.foot,
        min_age=args.min_age,
        max_age=args.max_age,
        limit=args.limit,
        sort_by=args.sort_by,
    )

    print(json.dumps([p.to_dict() for p in results], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
