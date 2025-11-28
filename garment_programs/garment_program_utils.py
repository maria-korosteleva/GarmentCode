"""Utility functions for garment program attachment constraint processing."""

from typing import Any, Callable, Type

from loguru import logger

from pygarment.meshgen.box_mesh_gen.stitch_types import EdgeLabel as BoxEdgeLabel


class AttachmentHandler:
    """Static class for handling attachment constraint processing."""
    
    @staticmethod
    def process_lower_interface_constraint(
        constraint: Any,
        box_mesh: Any,
        label_value: str
    ) -> list[int] | None:
        """
        Process LOWER_INTERFACE constraint by using vertices already labeled from edges.
        
        Parameters
        ----------
        constraint : AttachmentConstraint
            The attachment constraint to process.
        box_mesh : BoxMesh
            The BoxMesh instance containing the vertices.
        label_value : str
            The string value of the constraint label.
            
        Returns
        -------
        list[int] | None
            List of vertex IDs if found, None otherwise.
        """
        if label_value in box_mesh.vertex_labels:
            vertices = box_mesh.vertex_labels[label_value]
            logger.debug(
                f"Using {len(vertices)} already-labeled vertices for LOWER_INTERFACE constraint"
            )
            return vertices
        else:
            logger.warning(
                f"No vertices found with label {label_value} for LOWER_INTERFACE constraint"
            )
            return None

    @staticmethod
    def process_crotch_constraint(
        constraint: Any,
        box_mesh: Any
    ) -> list[int] | None:
        """
        Process CROTCH constraint by finding edges, then finding all vertices below in Y direction.
        
        Parameters
        ----------
        constraint : AttachmentConstraint
            The attachment constraint to process.
        box_mesh : BoxMesh
            The BoxMesh instance containing the vertices.
            
        Returns
        -------
        list[int] | None
            List of vertex IDs below the crotch point, None if no reference vertices found.
        """
        if not constraint.vertex_labels_to_find:
            logger.warning("CROTCH constraint has no vertex_labels_to_find")
            return None
        
        # Find reference vertices from CROTCH_POINT_SEAM edges
        labels_to_find = constraint.vertex_labels_to_find_enums
        reference_vertices = box_mesh.find_vertices_by_edge_labels(labels_to_find)
        
        if not reference_vertices:
            logger.warning(
                f"No reference vertices found for CROTCH constraint "
                f"with labels {[label.value for label in labels_to_find]}"
            )
            return None
        
        # Find all vertices below the crotch point in Y direction
        crotch_y_values = [box_mesh.vertices[v_id][1] for v_id in reference_vertices]
        min_crotch_y = min(crotch_y_values)
        
        vertices = [
            i for i, v in enumerate(box_mesh.vertices) 
            if v[1] < min_crotch_y
        ]
        
        logger.debug(
            f"Processed CROTCH constraint: found {len(vertices)} vertices "
            f"below crotch point (y < {min_crotch_y:.2f})"
        )
        
        return vertices

    @staticmethod
    def process_default_constraint(
        constraint: Any,
        box_mesh: Any,
        label_value: str
    ) -> list[int] | None:
        """
        Process constraint with default behavior: find vertices from edge labels.
        
        Parameters
        ----------
        constraint : AttachmentConstraint
            The attachment constraint to process.
        box_mesh : BoxMesh
            The BoxMesh instance containing the vertices.
        label_value : str
            The string value of the constraint label.
            
        Returns
        -------
        list[int] | None
            List of vertex IDs found from edge labels, None if no labels to find.
        """
        if not constraint.vertex_labels_to_find:
            return None
        
        logger.info(
            f"Processing constraint {label_value} with default behavior: "
            f"finding vertices from edge labels"
        )
        labels_to_find = constraint.vertex_labels_to_find_enums
        vertices = box_mesh.find_vertices_by_edge_labels(labels_to_find)
        return vertices

    @staticmethod
    def label_vertices(
        box_mesh: Any,
        label_value: str,
        vertices: list[int]
    ) -> None:
        """
        Label vertices in the box mesh, removing duplicates.
        
        Parameters
        ----------
        box_mesh : BoxMesh
            The BoxMesh instance to label vertices in.
        label_value : str
            The label to apply to the vertices.
        vertices : list[int]
            List of vertex IDs to label.
        """
        if not vertices:
            logger.warning(
                f"No final vertices to label for constraint {label_value}"
            )
            return
        
        # Remove duplicates while preserving order
        unique_vertices = list(dict.fromkeys(vertices))
        box_mesh.vertex_labels.setdefault(label_value, []).extend(unique_vertices)
        logger.debug(
            f"Labeled {len(unique_vertices)} vertices with label {label_value}"
        )

    @staticmethod
    def process_attachment_constraints_generic(
        garment_class: Type[Any],
        box_mesh: Any,
        constraint_processors: dict[BoxEdgeLabel, Callable[[Any, Any], list[int] | None]] | None = None
    ) -> None:
        """
        Generic function to process attachment constraints for any garment class.
        
        This function handles the common flow:
        1. Get constraints from the garment class
        2. Store constraints in BoxMesh
        3. Process each constraint using provided processors or default behavior
        4. Label vertices
        
        Parameters
        ----------
        garment_class : Type
            The garment class to get constraints from (must have get_attachment_constraints static method).
        box_mesh : BoxMesh
            The BoxMesh instance to process constraints for.
        constraint_processors : dict[BoxEdgeLabel, Callable], optional
            Dictionary mapping constraint labels to custom processor functions.
            If a constraint label is not in this dict, default behavior is used.
            Processor functions should take (constraint, box_mesh) and return list[int] | None.
        """
        # Get constraints from garment class
        constraints = garment_class.get_attachment_constraints()
        
        if not constraints:
            logger.debug(f"No attachment constraints found for {garment_class.__name__}")
            return
        
        # Store constraints in BoxMesh for later use
        box_mesh.attachment_constraints = constraints
        
        # Default processors for common constraint types
        default_processors = {
            BoxEdgeLabel.LOWER_INTERFACE: lambda c, bm: AttachmentHandler.process_lower_interface_constraint(
                c, bm, c.label_enum.value
            ),
            BoxEdgeLabel.CROTCH: AttachmentHandler.process_crotch_constraint,
        }
        
        # Merge with provided processors (provided ones take precedence)
        if constraint_processors:
            processors = {**default_processors, **constraint_processors}
        else:
            processors = default_processors
        
        # Process each constraint
        for constraint in constraints:
            constraint_label = constraint.label_enum
            label_value = constraint_label.value
            
            if not constraint.vertex_labels_to_find:
                logger.warning(
                    f"Constraint with label {label_value} has no vertex_labels_to_find. Skipping."
                )
                continue
            
            # Get processor for this constraint type
            if constraint_label in processors:
                vertices = processors[constraint_label](constraint, box_mesh)
                if vertices is None:
                    continue
            else:
                # Use default behavior
                vertices = AttachmentHandler.process_default_constraint(constraint, box_mesh, label_value)
                if vertices is None:
                    continue
            
            # Label the vertices
            AttachmentHandler.label_vertices(box_mesh, label_value, vertices)

    @staticmethod
    def create_default_vertex_processor(garment_class: Type[Any]) -> Callable[[Any], None]:
        """
        Create a default vertex processor callback for garments with no special handling.
        
        Parameters
        ----------
        garment_class : Type
            The garment class to create a processor for.
            
        Returns
        -------
        Callable[[BoxMesh], None]
            A vertex processor callback function.
        """
        def processor(box_mesh: Any) -> None:
            """Default vertex processor that uses generic constraint processing."""
            AttachmentHandler.process_attachment_constraints_generic(garment_class, box_mesh)
        
        return processor
