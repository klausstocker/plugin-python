using System;
using System.Collections.Generic;
using System.Drawing;
using System.Drawing.Drawing2D;
using System.Linq;
using System.Windows.Forms;

namespace SubwaySurferWinForms;

internal sealed class GameForm : Form
{
    private const int LaneCount = 3;
    private const int PlayerLaneY = 505;
    private const int PlayerSize = 52;
    private const int ObjectSize = 42;
    private const int JumpDurationTicks = 24;

    private readonly Timer _gameTimer = new() { Interval = 16 };
    private readonly Random _random = new();
    private readonly List<GameObject> _objects = [];

    private int _playerLane = 1;
    private int _score;
    private int _coins;
    private int _jumpTicksRemaining;
    private int _spawnTicks;
    private float _worldSpeed = 6.5f;
    private bool _gameOver;

    public GameForm()
    {
        Text = "Mini Subway Surfer";
        ClientSize = new Size(540, 720);
        MinimumSize = new Size(460, 620);
        BackColor = Color.FromArgb(18, 22, 31);
        DoubleBuffered = true;
        KeyPreview = true;

        _gameTimer.Tick += (_, _) => UpdateGame();
        KeyDown += OnKeyDown;
        ResetGame();
        _gameTimer.Start();
    }

    private void OnKeyDown(object? sender, KeyEventArgs e)
    {
        if (_gameOver && e.KeyCode == Keys.R)
        {
            ResetGame();
            return;
        }

        if (_gameOver)
        {
            return;
        }

        if (e.KeyCode is Keys.Left or Keys.A)
        {
            _playerLane = Math.Max(0, _playerLane - 1);
        }
        else if (e.KeyCode is Keys.Right or Keys.D)
        {
            _playerLane = Math.Min(LaneCount - 1, _playerLane + 1);
        }
        else if (e.KeyCode is Keys.Space or Keys.Up or Keys.W)
        {
            if (_jumpTicksRemaining == 0)
            {
                _jumpTicksRemaining = JumpDurationTicks;
            }
        }
    }

    private void ResetGame()
    {
        _objects.Clear();
        _playerLane = 1;
        _score = 0;
        _coins = 0;
        _jumpTicksRemaining = 0;
        _spawnTicks = 0;
        _worldSpeed = 6.5f;
        _gameOver = false;
    }

    private void UpdateGame()
    {
        if (_gameOver)
        {
            Invalidate();
            return;
        }

        _score++;
        _worldSpeed = Math.Min(14f, 6.5f + _score / 650f);

        if (_jumpTicksRemaining > 0)
        {
            _jumpTicksRemaining--;
        }

        _spawnTicks--;
        if (_spawnTicks <= 0)
        {
            SpawnObjectWave();
            _spawnTicks = Math.Max(24, 78 - _score / 80);
        }

        foreach (GameObject item in _objects)
        {
            item.Y += _worldSpeed;
        }

        RectangleF playerBounds = GetPlayerBounds();
        foreach (GameObject item in _objects.ToArray())
        {
            RectangleF itemBounds = item.Bounds(GetLaneCenter(item.Lane), ObjectSize);
            if (!playerBounds.IntersectsWith(itemBounds) || item.Lane != _playerLane)
            {
                continue;
            }

            if (item.Kind == PickupKind.Coin)
            {
                _coins++;
                _score += 25;
                _objects.Remove(item);
            }
            else if (_jumpTicksRemaining == 0)
            {
                _gameOver = true;
                break;
            }
        }

        _objects.RemoveAll(item => item.Y > ClientSize.Height + ObjectSize);
        Invalidate();
    }

    private void SpawnObjectWave()
    {
        int safeLane = _random.Next(LaneCount);
        for (int lane = 0; lane < LaneCount; lane++)
        {
            bool spawnObstacle = lane != safeLane && _random.NextDouble() < 0.45;
            bool spawnCoin = !spawnObstacle && _random.NextDouble() < 0.35;

            if (spawnObstacle)
            {
                _objects.Add(new GameObject(lane, -ObjectSize, PickupKind.Obstacle));
            }
            else if (spawnCoin)
            {
                _objects.Add(new GameObject(lane, -ObjectSize, PickupKind.Coin));
            }
        }
    }

    private RectangleF GetPlayerBounds()
    {
        float jumpOffset = GetJumpOffset();
        float centerX = GetLaneCenter(_playerLane);
        return new RectangleF(
            centerX - PlayerSize / 2f,
            PlayerLaneY - jumpOffset - PlayerSize / 2f,
            PlayerSize,
            PlayerSize);
    }

    private float GetJumpOffset()
    {
        if (_jumpTicksRemaining == 0)
        {
            return 0;
        }

        double progress = 1.0 - _jumpTicksRemaining / (double)JumpDurationTicks;
        return (float)(Math.Sin(progress * Math.PI) * 90.0);
    }

    private float GetLaneCenter(int lane)
    {
        float trackWidth = ClientSize.Width * 0.72f;
        float left = (ClientSize.Width - trackWidth) / 2f;
        return left + trackWidth / LaneCount * (lane + 0.5f);
    }

    protected override void OnPaint(PaintEventArgs e)
    {
        base.OnPaint(e);
        Graphics g = e.Graphics;
        g.SmoothingMode = SmoothingMode.AntiAlias;

        DrawTrack(g);
        DrawObjects(g);
        DrawPlayer(g);
        DrawHud(g);

        if (_gameOver)
        {
            DrawGameOver(g);
        }
    }

    private void DrawTrack(Graphics g)
    {
        Rectangle track = new(
            (int)(ClientSize.Width * 0.14f),
            0,
            (int)(ClientSize.Width * 0.72f),
            ClientSize.Height);

        using LinearGradientBrush trackBrush = new(track, Color.FromArgb(39, 44, 58), Color.FromArgb(20, 24, 34), 90f);
        g.FillRectangle(trackBrush, track);

        using Pen sidePen = new(Color.FromArgb(255, 199, 63), 5f);
        g.DrawLine(sidePen, track.Left, 0, track.Left, ClientSize.Height);
        g.DrawLine(sidePen, track.Right, 0, track.Right, ClientSize.Height);

        using Pen lanePen = new(Color.FromArgb(120, 255, 255, 255), 3f) { DashStyle = DashStyle.Dash };
        for (int lane = 1; lane < LaneCount; lane++)
        {
            float x = track.Left + track.Width / (float)LaneCount * lane;
            g.DrawLine(lanePen, x, 0, x, ClientSize.Height);
        }
    }

    private void DrawObjects(Graphics g)
    {
        foreach (GameObject item in _objects)
        {
            RectangleF bounds = item.Bounds(GetLaneCenter(item.Lane), ObjectSize);
            if (item.Kind == PickupKind.Coin)
            {
                using Brush coinBrush = new SolidBrush(Color.Gold);
                using Pen coinPen = new(Color.FromArgb(255, 238, 120), 3f);
                g.FillEllipse(coinBrush, bounds);
                g.DrawEllipse(coinPen, bounds);
            }
            else
            {
                using Brush obstacleBrush = new SolidBrush(Color.FromArgb(219, 65, 65));
                g.FillRectangle(obstacleBrush, bounds);
                using Pen warningPen = new(Color.White, 3f);
                g.DrawLine(warningPen, bounds.Left + 10, bounds.Top + 10, bounds.Right - 10, bounds.Bottom - 10);
                g.DrawLine(warningPen, bounds.Right - 10, bounds.Top + 10, bounds.Left + 10, bounds.Bottom - 10);
            }
        }
    }

    private void DrawPlayer(Graphics g)
    {
        RectangleF player = GetPlayerBounds();
        using Brush shadowBrush = new SolidBrush(Color.FromArgb(80, 0, 0, 0));
        g.FillEllipse(shadowBrush, player.X + 6, PlayerLaneY + 22, player.Width - 12, 14);

        using Brush playerBrush = new SolidBrush(Color.FromArgb(61, 168, 255));
        g.FillEllipse(playerBrush, player);

        using Brush faceBrush = new SolidBrush(Color.White);
        g.FillEllipse(faceBrush, player.X + 12, player.Y + 14, 9, 9);
        g.FillEllipse(faceBrush, player.Right - 21, player.Y + 14, 9, 9);
    }

    private void DrawHud(Graphics g)
    {
        using Font titleFont = new("Segoe UI", 16f, FontStyle.Bold);
        using Font helpFont = new("Segoe UI", 10f, FontStyle.Regular);
        using Brush textBrush = new SolidBrush(Color.White);
        using Brush mutedBrush = new SolidBrush(Color.FromArgb(190, 255, 255, 255));

        g.DrawString($"Score: {_score}", titleFont, textBrush, 18, 16);
        g.DrawString($"Coins: {_coins}", titleFont, textBrush, 18, 46);
        g.DrawString("←/→ oder A/D bewegen · Space/W springen", helpFont, mutedBrush, 18, ClientSize.Height - 34);
    }

    private void DrawGameOver(Graphics g)
    {
        using Brush overlay = new SolidBrush(Color.FromArgb(185, 0, 0, 0));
        g.FillRectangle(overlay, ClientRectangle);

        using Font headline = new("Segoe UI", 28f, FontStyle.Bold);
        using Font details = new("Segoe UI", 14f, FontStyle.Regular);
        using Brush textBrush = new SolidBrush(Color.White);

        const string title = "Game Over";
        const string restart = "Drücke R für einen Neustart";
        SizeF titleSize = g.MeasureString(title, headline);
        SizeF restartSize = g.MeasureString(restart, details);

        g.DrawString(title, headline, textBrush, (ClientSize.Width - titleSize.Width) / 2f, ClientSize.Height / 2f - 70);
        g.DrawString($"Score: {_score}  ·  Coins: {_coins}", details, textBrush, ClientSize.Width / 2f - 95, ClientSize.Height / 2f - 15);
        g.DrawString(restart, details, textBrush, (ClientSize.Width - restartSize.Width) / 2f, ClientSize.Height / 2f + 26);
    }
}
