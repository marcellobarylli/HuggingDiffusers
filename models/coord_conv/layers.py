import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import Tuple, Optional


class AddCoordinateChannels(nn.Module):
    """
    Transform that adds coordinate channels to images based on the CoordConv paper
    (https://arxiv.org/abs/1807.03247)
    """
    
    def __init__(self, 
                 with_r: bool = False, 
                 normalize: bool = True,
                 coord_size: Optional[Tuple[int, int]] = None):
        """
        Initialize the coordinate channel adder.
        
        Args:
            with_r: Whether to include a radius channel
            normalize: Whether to normalize coordinate values to [-1, 1]
            coord_size: Size of the coordinate grid (height, width), if None will use input size
        """
        super().__init__()
        self.with_r = with_r
        self.normalize = normalize
        self.coord_size = coord_size
        
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Add coordinate channels to the input tensor.
        
        Args:
            x: Input tensor of shape (B, C, H, W)
            
        Returns:
            Tensor with added coordinate channels (B, C+2(+1), H, W)
        """
        batch_size, _, height, width = x.size()
        
        # Use specified size or input size
        h, w = self.coord_size if self.coord_size else (height, width)
        
        # Create coordinate grid
        y_coords = torch.linspace(-1 if self.normalize else 0, 
                                 1 if self.normalize else h-1, 
                                 h)
        x_coords = torch.linspace(-1 if self.normalize else 0, 
                                 1 if self.normalize else w-1, 
                                 w)
        
        # Meshgrid to create 2D coordinate grid
        y_coords, x_coords = torch.meshgrid(y_coords, x_coords, indexing='ij')
        
        # Add batch dimension and move to same device as input
        y_coords = y_coords.unsqueeze(0).repeat(batch_size, 1, 1).unsqueeze(1).to(x.device)
        x_coords = x_coords.unsqueeze(0).repeat(batch_size, 1, 1).unsqueeze(1).to(x.device)
        
        # Resize to match input if needed
        if (h, w) != (height, width):
            y_coords = F.interpolate(y_coords, size=(height, width), mode='bilinear', align_corners=True)
            x_coords = F.interpolate(x_coords, size=(height, width), mode='bilinear', align_corners=True)
        
        # Concatenate coordinate channels with input
        out = torch.cat([x, y_coords, x_coords], dim=1)
        
        # Add radius channel if requested
        if self.with_r:
            r = torch.sqrt(y_coords**2 + x_coords**2)  # Euclidean distance from center
            r = r / torch.max(r) if self.normalize else r  # Normalize if requested
            out = torch.cat([out, r], dim=1)
            
        return out 

class SymmetricCoordinateChannels(AddCoordinateChannels):
    """
    Transform that adds coordinate channels to images, with optional symmetric coordinate support.
    When use_symmetric=False, behaves exactly like AddCoordinateChannels.
    When use_symmetric=True, enforces symmetry in the coordinate space.
    """
    
    def __init__(self, 
                 use_symmetric: bool = False,  # Whether to use symmetric coordinates
                 symmetry_type: str = 'vertical',  # 'vertical', 'horizontal', 'both'
                 with_r: bool = False, 
                 normalize: bool = True,
                 coord_size: Optional[Tuple[int, int]] = None):
        """
        Initialize the coordinate channel adder.
        
        Args:
            use_symmetric: Whether to use symmetric coordinates (default: False, behaves like AddCoordinateChannels)
            symmetry_type: Type of symmetry to enforce ('vertical', 'horizontal', 'both') when use_symmetric=True
            with_r: Whether to include a radius channel
            normalize: Whether to normalize coordinate values to [-1, 1]
            coord_size: Size of the coordinate grid (height, width), if None will use input size
        """
        super().__init__(with_r=with_r, normalize=normalize, coord_size=coord_size)
        self.use_symmetric = use_symmetric
        self.symmetry_type = symmetry_type
        
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Add coordinate channels to the input tensor.
        If use_symmetric=True, enforces symmetry in the coordinate space.
        
        Args:
            x: Input tensor of shape (B, C, H, W)
            
        Returns:
            Tensor with added coordinate channels (B, C+2(+1), H, W)
        """
        batch_size, _, height, width = x.size()
        
        # Use specified size or input size
        h, w = self.coord_size if self.coord_size else (height, width)
        
        # Create coordinate grid
        y_coords = torch.linspace(-1 if self.normalize else 0, 
                                 1 if self.normalize else h-1, 
                                 h)
        x_coords = torch.linspace(-1 if self.normalize else 0, 
                                 1 if self.normalize else w-1, 
                                 w)
        
        # Meshgrid to create 2D coordinate grid
        y_coords, x_coords = torch.meshgrid(y_coords, x_coords, indexing='ij')
        
        # Apply symmetry transformations only if use_symmetric is True
        if self.use_symmetric:
            if self.symmetry_type in ['vertical', 'both']:
                # For vertical symmetry, we take absolute value of x-coordinate
                # This makes the left and right sides of the image identical in coordinate space
                x_coords = torch.abs(x_coords)
                if self.normalize:
                    # Re-normalize to [-1, 1] range
                    x_coords = x_coords * 2 - 1
                    
            if self.symmetry_type in ['horizontal', 'both']:
                # For horizontal symmetry, we take absolute value of y-coordinate
                y_coords = torch.abs(y_coords)
                if self.normalize:
                    # Re-normalize to [-1, 1] range
                    y_coords = y_coords * 2 - 1
        
        # Add batch dimension and move to same device as input
        y_coords = y_coords.unsqueeze(0).repeat(batch_size, 1, 1).unsqueeze(1).to(x.device)
        x_coords = x_coords.unsqueeze(0).repeat(batch_size, 1, 1).unsqueeze(1).to(x.device)
        
        # Resize to match input if needed
        if (h, w) != (height, width):
            y_coords = F.interpolate(y_coords, size=(height, width), mode='bilinear', align_corners=True)
            x_coords = F.interpolate(x_coords, size=(height, width), mode='bilinear', align_corners=True)
        
        # Concatenate coordinate channels with input
        out = torch.cat([x, y_coords, x_coords], dim=1)
        
        # Add radius channel if requested
        if self.with_r:
            r = torch.sqrt(y_coords**2 + x_coords**2)  # Euclidean distance from center
            r = r / torch.max(r) if self.normalize else r  # Normalize if requested
            out = torch.cat([out, r], dim=1)
            
        return out 