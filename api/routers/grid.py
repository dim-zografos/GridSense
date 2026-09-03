from fastapi import APIRouter, HTTPException, Query
from db.neo4j import get_driver
from models.graph import AffectedNode, FaultImpactResponse, RestorePath, RestorePathsResponse, NodeCreate, NodeCreateResponse, RelationshipCreate, RelationshipCreateResponse

router = APIRouter(prefix="/grid")

@router.get("/fault-impact/{node_id}", response_model=FaultImpactResponse)
async def get_fault_impact(
    node_id: str,
    max_depth: int = Query(6, ge=1, le=10)
):
    driver = get_driver()

    cypher = f"""
        MATCH (origin {{node_id: $node_id}})
        MATCH path = (origin)-[:FEEDS|SUPPLIES|CONNECTS_TO*1..{max_depth}]->(downstream)
        WITH downstream, min(length(path)) AS depth
        RETURN downstream.node_id AS node_id, labels(downstream)[0] AS node_type, downstream.name AS name, depth
        ORDER BY depth, node_id
    """

    async with driver.session(database="neo4j") as session:
        result = await session.run(
            cypher,
            node_id=node_id
        )

        records = await result.data()

        if not records:
            exists_result = await session.run(
                """
                MATCH (n {node_id: $node_id})
                RETURN n.node_id AS node_id
                """,
                node_id=node_id
            )

            exists = await exists_result.single()
            if exists is None: raise HTTPException(status_code=404, detail=f"Node '{node_id}' not found")

    affected_nodes = [
        AffectedNode(**record)
        for record in records
    ]

    return FaultImpactResponse(
        origin_id=node_id,
        affected_nodes=affected_nodes,
        total_affected=len(affected_nodes)
    )

@router.get("/restore-paths/{node_id}", response_model=RestorePathsResponse)
async def get_restore_paths(
    node_id: str,
    max_depth: int = Query(6, ge=1, le=10)
):
    driver = get_driver()

    cypher = f"""
        MATCH path = (source:GridSupplyPoint)
            -[:FEEDS|SUPPLIES|CONNECTS_TO*1..{max_depth}]->
            (target {{node_id: $node_id}})
        RETURN source.node_id AS source_id,
               [n IN nodes(path) | n.node_id] AS path_nodes,
               length(path) AS hops,
               all(
                   r IN relationships(path)
                   WHERE coalesce(r.active, false) = true
               ) AS active
        ORDER BY active DESC, hops, source_id
    """

    async with driver.session(database="neo4j") as session:
        result = await session.run(
            cypher,
            node_id=node_id
        )

        records = await result.data()

        if not records:
            exists_result = await session.run(
                """
                MATCH (n {node_id: $node_id})
                RETURN n.node_id AS node_id
                """,
                node_id=node_id
            )

            exists = await exists_result.single()
            if exists is None:raise HTTPException( status_code=404, detail=f"Node '{node_id}' not found")

    paths = [RestorePath(**record) for record in records]

    return RestorePathsResponse(
        node_id=node_id,
        paths=paths,
        total_paths=len(paths)
    )

NODE_LABELS = {
    "GridSupplyPoint": "GridSupplyPoint",
    "Substation": "Substation",
    "Transformer": "Transformer",
    "SmartMeter": "SmartMeter"
}

@router.post("/nodes", response_model=NodeCreateResponse, status_code=201)
async def create_node(node: NodeCreate):
    driver = get_driver()

    label = NODE_LABELS[node.node_type]

    properties = node.model_dump(
        exclude={"node_type"}
    )

    async with driver.session(database="neo4j") as session:
        exists_result = await session.run(
            """
            MATCH (n {node_id: $node_id})
            RETURN n.node_id AS node_id
            LIMIT 1
            """,
            node_id=node.node_id
        )

        existing = await exists_result.single()

        if existing is not None:
            raise HTTPException(
                status_code=409,
                detail=f"Node '{node.node_id}' already exists"
            )

        cypher = f"""
            CREATE (n:{label})
            SET n = $properties
            RETURN n.node_id AS node_id
        """

        result = await session.run( cypher, properties=properties)

        await result.single()

    return NodeCreateResponse(
        message=f"{node.node_type} created successfully",
        node_id=node.node_id,
        node_type=node.node_type
    )

@router.post("/relationships", response_model=RelationshipCreateResponse, status_code=201)
async def create_relationship(relationship: RelationshipCreate):
    driver = get_driver()

    expected_labels = {
        "FEEDS": ("GridSupplyPoint", "Substation"),
        "SUPPLIES": ("Substation", "Transformer"),
        "CONNECTS_TO": ("Transformer", "SmartMeter")
    }

    from_label, to_label = expected_labels[relationship.relationship_type]

    async with driver.session(database="neo4j") as session:
        nodes_result = await session.run(
            """
            MATCH (from_node {node_id: $from_id})
            MATCH (to_node {node_id: $to_id})
            RETURN labels(from_node)[0] AS from_label,
                   labels(to_node)[0] AS to_label
            """,
            from_id=relationship.from_id,
            to_id=relationship.to_id
        )

        nodes = await nodes_result.single()

        if nodes is None:
            raise HTTPException(status_code=404, detail="One or both nodes were not found")

        if (
            nodes["from_label"] != from_label
            or nodes["to_label"] != to_label
        ):
            raise HTTPException(
                status_code=400,
                detail=(
                    f"{relationship.relationship_type} requires "
                    f"{from_label} -> {to_label}"
                )
            )

        duplicate_result = await session.run(
            f"""
            MATCH (from_node {{node_id: $from_id}})
                  -[r:{relationship.relationship_type}]->
                  (to_node {{node_id: $to_id}})
            RETURN r
            LIMIT 1
            """,
            from_id=relationship.from_id,
            to_id=relationship.to_id
        )
        duplicate = await duplicate_result.single()
        if duplicate is not None: raise HTTPException(status_code=409, detail=(f"{relationship.relationship_type} relationship from '{relationship.from_id}' to '{relationship.to_id}' already exists"))

        properties = relationship.model_dump(
            exclude={
                "relationship_type",
                "from_id",
                "to_id"
            }
        )

        rel_type = relationship.relationship_type

        cypher = f"""
            MATCH (from_node {{node_id: $from_id}})
            MATCH (to_node {{node_id: $to_id}})
            CREATE (from_node)-[r:{rel_type}]->(to_node)
            SET r = $properties
            RETURN type(r) AS relationship_type
        """

        result = await session.run(
            cypher,
            from_id=relationship.from_id,
            to_id=relationship.to_id,
            properties=properties
        )

        await result.single()

    return RelationshipCreateResponse(
        message=f"{relationship.relationship_type} relationship created successfully",
        from_id=relationship.from_id,
        to_id=relationship.to_id,
        relationship_type=relationship.relationship_type
    )