import os
from datetime import datetime

import click
from alembic import command
from alembic.config import Config
from flask import Flask, jsonify, request
from flask.cli import with_appcontext

from enpoints import (endpoint_author_similarity_score,
                      endpoint_connected_posts, endpoint_dataframe,
                      endpoint_get_articles, endpoint_get_authors,
                      endpoint_get_content, endpoint_similarity_score,
                      endpoint_specter_clustering)
from utils import create_idea, list_ideas

app = Flask(__name__)

@app.cli.command("db_migrate")
@click.option("--message", default=None, help="Revision message")
@with_appcontext
def db_migrate(message):
    alembic_cfg = Config("alembic.ini")
    command.revision(alembic_cfg, message=message, autogenerate=True)

@app.cli.command("db_upgrade")
@with_appcontext
def db_upgrade():
    alembic_cfg = Config("alembic.ini")
    command.upgrade(alembic_cfg, "head")


def is_array_empty(array):
    return array is None or len(array) == 0

@app.route('/api/authors', methods=['GET'])
def get_authors():
    return jsonify({
        'data': endpoint_get_authors()
    })

@app.route('/api/articles', methods=['GET'])
def get_articles():
    return jsonify({
        'data': endpoint_get_articles()
    })

@app.route('/api/content', methods=['GET'])
def get_content():
    return jsonify({
        'data': endpoint_get_content()
    })


@app.route('/api/dataframe', methods=['GET'])
def get_dataframe():
    params = request.args.to_dict(flat=False)

    columns = []
    ascendings = []

    for key, value in params.items():
        if key.startswith('columns[') and key.endswith(']'):
            name = key[8:-1]
            columns.append(name)
            ascendings.append(value[0] == 'asc')

    try:
        data = endpoint_dataframe(columns, ascendings)
        return jsonify(data)
    except:
        return []

@app.route('/api/similarity-score', methods=['GET'])
def get_similarity_score():
    params = request.args.to_dict(flat=False)
    article_list = params.get('article_list[]')
    compared_authors = params.get('compared_authors[]')
    author_pair1 = params.get('author_pair1[]')
    author_pair2 = params.get('author_pair2[]')

    articles_result = []

    if(is_array_empty(article_list) == False):
        articles_result = endpoint_similarity_score(article_list, compared_authors)

    return jsonify({
        'authors': endpoint_author_similarity_score(
            author_pair1,
            author_pair2
        ).tolist(),
        'articles': articles_result
    })

@app.route('/api/specter-clustering', methods=['GET'])
def get_specter_clustering():
    n = int(request.args.get('cluster_count'))
    cluster_choice = int(request.args.get('cluster'))
    select_by_content = request.args.get('content')
    return jsonify(endpoint_specter_clustering(n, cluster_choice, select_by_content))

@app.route('/api/connected-posts', methods=['GET'])
def get_connected_posts():
    depth = int(request.args.get('depth'))
    a_name = request.args.get('a_name')
    return jsonify(endpoint_connected_posts(a_name, depth))

@app.route('/api/ideas', methods=['GET'])
def get_ideas():
    limit = request.args.get('limit', default=10, type=int)
    last_endorsement_count = request.args.get('lastEndorsementCount', type=int)
    last_created_at = request.args.get('lastCreatedAt')
    last_id = request.args.get('lastId', type=int)

    if last_created_at:
        last_created_at = datetime.fromisoformat(last_created_at)

    ideas, next_cursor = list_ideas(limit, last_endorsement_count, last_created_at, last_id)
    ideas_list = [
        {
            "id": idea[0],
            "main_article": idea[1],
            "node_id": idea[2],
            "link": idea[3],
            "type": idea[4],
            "label": idea[5],
            "created_at": idea[6].isoformat(),
            "endorsement_count": idea[7],
            "endorsements": [
                {
                    "email": endorsement[0],
                    "comment": endorsement[1],
                    "created_at": endorsement[2].isoformat()
                }
                for endorsement in idea[8]
            ]
        }
        for idea in ideas
    ]

    next_params = {}
    if next_cursor:
        next_endorsement_count, next_created_at, next_id = next_cursor.split('_')
        next_params = {
            'lastEndorsementCount': next_endorsement_count,
            'lastCreatedAt': next_created_at,
            'lastId': next_id
        }

    return jsonify({
        "ideas": ideas_list,
        "nextParams": next_params
    })

@app.route('/api/ideas', methods=['POST'])
def create_new_idea():
    data = request.json
    main_article = data.get('mainArticle')
    node_id = data.get('nodeId')
    link = data.get('link')
    type = data.get('type')
    label = data.get('label')
    comment = data.get('comment')
    email = data.get('email')

    if not node_id or not link:
        return jsonify({"error": "Node ID and link are required"}), 400

    idea_id, new_count, is_endorsement = create_idea(main_article, node_id, link, type, label, email, comment)
    
    return jsonify({
        "success": True, 
        "message": "Idea endorsed successfully" if is_endorsement else "Idea shared successfully",
        "id": idea_id,
        "endorsement_count": new_count
    }), 201

if __name__ == '__main__':
    app.run(port=5000, debug=True)
