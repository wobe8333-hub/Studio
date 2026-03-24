"""
Generate Fixtures - 실제 asset 스키마를 복제한 fixtures 생성

카테고리별 최소 60개 이상의 asset fixtures를 생성합니다.
"""

import json
import uuid
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any


def generate_fixture_asset(
    category: str,
    keyword: str,
    index: int,
    base_payload: Dict[str, Any]
) -> Dict[str, Any]:
    """fixture asset 생성"""
    asset_id = f"fixture_asset_{category}_{index:03d}"
    
    # base_payload를 복제하고 키워드/카테고리 업데이트
    payload = dict(base_payload)
    payload["keyword"] = keyword
    payload["category"] = category
    payload["title"] = f"{keyword} - {category.title()} Topic {index}"
    
    # raw_hash는 나중에 계산됨
    raw_hash = f"fixture_hash_{category}_{index:03d}"
    
    return {
        "asset_id": asset_id,
        "category": category,
        "keywords": [keyword],
        "source_id": "fixtures",
        "source_ref": "fixtures://assets_schema.jsonl",
        "fetched_at": datetime.utcnow().isoformat() + "Z",
        "raw_hash": raw_hash,
        "license_status": "KNOWN",
        "usage_rights": "ALLOWED",
        "trust_level": "MEDIUM",
        "impact_scope": "LOW",
        "lifecycle_state": "RAW",
        "payload": payload,
        "license_source": "INTERNAL_SYNTHETIC"
    }


def main():
    """메인 함수"""
    fixtures_dir = Path(__file__).resolve().parent.parent / "knowledge_v1" / "fixtures"
    fixtures_dir.mkdir(parents=True, exist_ok=True)
    
    fixtures_path = fixtures_dir / "assets_schema.jsonl"
    
    # 기본 payload 템플릿 (실제 asset 스키마 기반)
    base_payloads = {
        "science": {
            "text": "Scientific knowledge encompasses the systematic study of the natural world through observation and experimentation. It provides evidence-based understanding of physical, biological, and chemical phenomena.",
            "summary": "Scientific knowledge is evidence-based understanding of natural phenomena."
        },
        "history": {
            "text": "Historical knowledge documents past events, cultures, and societies. It helps us understand how human civilization has evolved and how past events influence the present.",
            "summary": "Historical knowledge documents past events and their influence."
        },
        "economy": {
            "text": "Economic knowledge covers the production, distribution, and consumption of goods and services. It includes concepts like supply, demand, inflation, and market dynamics.",
            "summary": "Economic knowledge covers production, distribution, and consumption."
        },
        "geography": {
            "text": "Geographic knowledge includes understanding of Earth's physical features, climate patterns, and human-environment interactions. It covers continents, oceans, and spatial relationships.",
            "summary": "Geographic knowledge covers Earth's physical features and spatial relationships."
        },
        "common_sense": {
            "text": "Common sense knowledge represents everyday understanding that helps people navigate daily life. It includes practical knowledge about weather, health, and social interactions.",
            "summary": "Common sense knowledge represents everyday practical understanding."
        },
        "papers": {
            "text": "Academic papers present research findings and theoretical frameworks. They follow rigorous methodologies and peer review processes to establish reliable knowledge.",
            "summary": "Academic papers present rigorous research findings and frameworks."
        }
    }
    
    # 카테고리별 키워드 (각 카테고리당 60개 이상 생성)
    category_keywords = {
        "science": [
            "gravity", "quantum physics", "evolution", "climate change", "black hole",
            "atom", "molecule", "energy", "light", "wave", "relativity", "DNA", "cell",
            "photosynthesis", "magnetism", "electricity", "thermodynamics", "genetics",
            "chemistry", "biology", "physics", "astronomy", "geology", "ecology",
            "neuroscience", "biochemistry", "astrophysics", "particle physics", "optics",
            "acoustics", "mechanics", "electromagnetism", "nuclear physics", "cosmology",
            "microbiology", "zoology", "botany", "anatomy", "physiology", "immunology",
            "pharmacology", "toxicology", "epidemiology", "anthropology", "paleontology",
            "meteorology", "oceanography", "seismology", "volcanology", "hydrology",
            "glaciology", "mineralogy", "petrology", "geochemistry", "biogeography",
            "conservation biology", "environmental science", "sustainability", "renewable energy"
        ],
        "history": [
            "cold war", "world war", "ancient rome", "renaissance", "industrial revolution",
            "empire", "civilization", "medieval", "revolution", "dynasty", "crusades",
            "enlightenment", "reformation", "byzantine", "ancient greece", "egypt",
            "chinese dynasties", "mongol empire", "ottoman empire", "holy roman empire",
            "british empire", "american revolution", "french revolution", "russian revolution",
            "world war i", "world war ii", "vietnam war", "korean war", "gulf war",
            "renaissance art", "baroque", "gothic", "romanticism", "impressionism",
            "feudalism", "capitalism", "socialism", "communism", "fascism", "democracy",
            "monarchy", "republic", "confederation", "federation", "treaty", "alliance",
            "diplomacy", "colonialism", "imperialism", "nationalism", "independence",
            "migration", "trade routes", "silk road", "exploration", "discovery",
            "archaeology", "paleolithic", "neolithic", "bronze age", "iron age", "classical period"
        ],
        "economy": [
            "inflation", "gdp", "stock market", "cryptocurrency", "trade", "currency",
            "bank", "finance", "economic", "market", "supply", "demand", "price",
            "profit", "loss", "revenue", "expense", "budget", "investment", "savings",
            "debt", "credit", "interest", "loan", "mortgage", "insurance", "pension",
            "tax", "tariff", "subsidy", "welfare", "unemployment", "employment",
            "wages", "salary", "income", "wealth", "poverty", "inequality",
            "capitalism", "socialism", "communism", "mixed economy", "free market",
            "monopoly", "oligopoly", "competition", "monopolistic competition",
            "economic growth", "recession", "depression", "boom", "bust", "cycle",
            "fiscal policy", "monetary policy", "central bank", "reserve bank",
            "exchange rate", "foreign exchange", "balance of trade", "balance of payments",
            "globalization", "outsourcing", "offshoring", "e-commerce", "digital economy"
        ],
        "geography": [
            "latitude", "longitude", "tectonic plates", "ocean currents", "climate zones",
            "mountain", "river", "continent", "country", "map", "hemisphere", "equator",
            "tropics", "polar", "temperate", "desert", "tundra", "taiga", "savanna",
            "rainforest", "grassland", "wetland", "delta", "peninsula", "isthmus",
            "archipelago", "island", "volcano", "earthquake", "tsunami", "hurricane",
            "typhoon", "monsoon", "drought", "flood", "erosion", "deposition",
            "weathering", "glacier", "ice sheet", "permafrost", "watershed",
            "basin", "plateau", "plain", "valley", "canyon", "cave", "coral reef",
            "atoll", "fjord", "gulf", "bay", "strait", "channel", "current",
            "tide", "wave", "beach", "coast", "shore", "seabed", "continental shelf"
        ],
        "common_sense": [
            "electricity", "water cycle", "photosynthesis", "gravity", "magnetism",
            "light", "sound", "temperature", "pressure", "force", "motion", "energy",
            "matter", "state", "solid", "liquid", "gas", "plasma", "evaporation",
            "condensation", "freezing", "melting", "boiling", "cooking", "nutrition",
            "health", "exercise", "sleep", "hygiene", "safety", "first aid", "emergency",
            "weather", "season", "climate", "rain", "snow", "wind", "cloud", "sun",
            "moon", "day", "night", "time", "clock", "calendar", "year", "month",
            "week", "day", "hour", "minute", "second", "measurement", "length",
            "weight", "volume", "distance", "speed", "direction", "compass", "map",
            "direction", "north", "south", "east", "west", "navigation", "transportation"
        ],
        "papers": [
            "transformer", "attention mechanism", "neural network", "deep learning", "llm",
            "ai", "machine learning", "algorithm", "nlp", "computer vision", "reinforcement learning",
            "supervised learning", "unsupervised learning", "semi-supervised learning",
            "transfer learning", "few-shot learning", "zero-shot learning", "meta-learning",
            "optimization", "gradient descent", "backpropagation", "activation function",
            "loss function", "regularization", "dropout", "batch normalization", "layer normalization",
            "convolution", "pooling", "attention", "self-attention", "multi-head attention",
            "positional encoding", "embedding", "word embedding", "sentence embedding",
            "tokenization", "vocabulary", "corpus", "dataset", "preprocessing", "augmentation",
            "validation", "testing", "evaluation", "metrics", "accuracy", "precision",
            "recall", "f1 score", "bleu", "rouge", "perplexity", "cross-entropy",
            "generative model", "discriminative model", "generative adversarial network",
            "variational autoencoder", "diffusion model", "language model", "pre-training",
            "fine-tuning", "prompt engineering", "in-context learning", "chain of thought"
        ]
    }
    
    # 각 카테고리별로 최소 60개 이상 생성
    all_fixtures = []
    
    for category, keywords in category_keywords.items():
        base_payload = base_payloads.get(category, {
            "text": f"This is a knowledge asset about {category}.",
            "summary": f"Knowledge about {category}."
        })
        
        # 키워드가 60개 미만이면 반복 생성
        target_count = max(60, len(keywords))
        keyword_index = 0
        
        for i in range(target_count):
            keyword = keywords[keyword_index % len(keywords)]
            fixture_asset = generate_fixture_asset(category, keyword, i, base_payload)
            all_fixtures.append(fixture_asset)
            keyword_index += 1
    
    # JSONL 파일로 저장
    with open(fixtures_path, "w", encoding="utf-8") as f:
        for fixture in all_fixtures:
            f.write(json.dumps(fixture, ensure_ascii=False) + "\n")
    
    print(f"Generated {len(all_fixtures)} fixture assets")
    print(f"Saved to: {fixtures_path}")
    
    # 카테고리별 통계
    category_counts = {}
    for fixture in all_fixtures:
        cat = fixture["category"]
        category_counts[cat] = category_counts.get(cat, 0) + 1
    
    print("\nCategory counts:")
    for cat, count in sorted(category_counts.items()):
        print(f"  {cat}: {count}")


if __name__ == "__main__":
    main()

