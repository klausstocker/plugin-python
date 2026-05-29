using System.Drawing;

namespace SubwaySurferWinForms;

internal enum PickupKind
{
    Coin,
    Obstacle
}

internal sealed class GameObject
{
    public GameObject(int lane, float y, PickupKind kind)
    {
        Lane = lane;
        Y = y;
        Kind = kind;
    }

    public int Lane { get; }
    public float Y { get; set; }
    public PickupKind Kind { get; }

    public RectangleF Bounds(float laneCenter, float size)
    {
        return new RectangleF(laneCenter - size / 2f, Y - size / 2f, size, size);
    }
}
