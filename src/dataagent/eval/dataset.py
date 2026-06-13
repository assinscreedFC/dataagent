"""Jeu de 10 questions business Olist avec mots-clés attendus (D-01).

Chaque entrée : {"question": str, "expected_keywords": list[str]}.
Les mots-clés sont en minuscules et doivent être trouvables (substring
case-insensitive) dans un rapport correct produit par l'agent.
"""

QUESTIONS: list[dict] = [
    {
        "question": "Quel est le chiffre d'affaires total par mois en 2017 ?",
        "expected_keywords": ["chiffre", "order_items", "price", "2017", "mois"],
    },
    {
        "question": "Quelles sont les 5 catégories de produits générant le plus de revenus ?",
        "expected_keywords": ["catégorie", "product_category", "revenus", "top", "order_items"],
    },
    {
        "question": "Quel est le délai de livraison moyen par état brésilien ?",
        "expected_keywords": ["livraison", "orders", "jours", "état", "customer"],
    },
    {
        "question": "Y a-t-il une corrélation entre les retards de livraison et les notes d'avis clients ?",
        "expected_keywords": ["retard", "review_score", "livraison", "corrélation", "orders"],
    },
    {
        "question": "Quel est le score moyen des avis clients par catégorie de produit ?",
        "expected_keywords": ["score", "review", "catégorie", "produit", "moyen"],
    },
    {
        "question": "Quels vendeurs ont le plus grand volume de ventes en nombre de commandes ?",
        "expected_keywords": ["vendeur", "seller", "commandes", "volume", "order_items"],
    },
    {
        "question": "Quel est le coût de fret moyen par catégorie de produit ?",
        "expected_keywords": ["fret", "freight_value", "catégorie", "order_items", "moyen"],
    },
    {
        "question": "Combien de commandes ont été annulées et quelle est la proportion par rapport aux commandes livrées ?",
        "expected_keywords": ["annulée", "canceled", "livrée", "delivered", "proportion"],
    },
    {
        "question": "Quelle est la distribution géographique des clients (par état) ?",
        "expected_keywords": ["client", "customer", "état", "géographique", "distribution"],
    },
    {
        "question": "Quels sont les produits les plus achetés en termes de quantité ?",
        "expected_keywords": ["produit", "product", "quantité", "achetés", "top"],
    },
]
