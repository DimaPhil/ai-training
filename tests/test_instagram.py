"""Tests for Instagram crawler functionality."""

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

from src.instagram import (
    VideoList,
    VideoPost,
    _sleep_with_jitter,
    extract_shortcodes_from_html,
    load_video_list,
    save_video_list,
)


class TestVideoPost:
    """Tests for VideoPost model."""

    def test_video_post_creation(self) -> None:
        """Test creating a VideoPost."""
        post = VideoPost(
            shortcode="ABC123",
            url="https://www.instagram.com/p/ABC123/",
            video_url="https://cdn.instagram.com/video.mp4",
            caption="Great workout!",
        )
        assert post.shortcode == "ABC123"
        assert post.caption == "Great workout!"

    def test_video_post_without_caption(self) -> None:
        """Test VideoPost without caption."""
        post = VideoPost(
            shortcode="XYZ789",
            url="https://www.instagram.com/p/XYZ789/",
            video_url="https://cdn.instagram.com/video2.mp4",
        )
        assert post.caption is None


class TestVideoList:
    """Tests for VideoList model."""

    def test_video_list_creation(self) -> None:
        """Test creating a VideoList."""
        videos = [
            VideoPost(
                shortcode="A",
                url="https://www.instagram.com/p/A/",
                video_url="https://cdn.instagram.com/a.mp4",
            ),
            VideoPost(
                shortcode="B",
                url="https://www.instagram.com/p/B/",
                video_url="https://cdn.instagram.com/b.mp4",
            ),
        ]
        video_list = VideoList(profile="test_user", videos=videos)
        assert video_list.profile == "test_user"
        assert len(video_list.videos) == 2


class TestVideoListIO:
    """Tests for video list save/load functions."""

    def test_save_and_load_video_list(self) -> None:
        """Test saving and loading a video list."""
        videos = [
            VideoPost(
                shortcode="TEST1",
                url="https://www.instagram.com/p/TEST1/",
                video_url="https://cdn.instagram.com/test1.mp4",
                caption="Test caption 1",
            ),
            VideoPost(
                shortcode="TEST2",
                url="https://www.instagram.com/p/TEST2/",
                video_url="https://cdn.instagram.com/test2.mp4",
            ),
        ]
        original = VideoList(profile="test_profile", videos=videos)

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            file_path = Path(f.name)

        try:
            save_video_list(original, file_path)
            loaded = load_video_list(file_path)

            assert loaded.profile == original.profile
            assert len(loaded.videos) == len(original.videos)
            assert loaded.videos[0].shortcode == "TEST1"
            assert loaded.videos[1].shortcode == "TEST2"
        finally:
            file_path.unlink()

    def test_load_video_list_preserves_captions(self) -> None:
        """Test that captions are preserved during load."""
        data = {
            "profile": "test",
            "videos": [
                {
                    "shortcode": "A",
                    "url": "https://www.instagram.com/p/A/",
                    "video_url": "https://cdn.instagram.com/a.mp4",
                    "caption": "Caption preserved",
                }
            ],
        }
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(data, f)
            file_path = Path(f.name)

        try:
            loaded = load_video_list(file_path)
            assert loaded.videos[0].caption == "Caption preserved"
        finally:
            file_path.unlink()


class TestExtractShortcodes:
    """Tests for HTML shortcode extraction."""

    def test_extract_shortcodes_from_post_urls(self) -> None:
        """Test extracting shortcodes from /p/ URLs."""
        html = """
        <a href="/p/ABC12345678/">Post 1</a>
        <a href="/p/XYZ98765432/">Post 2</a>
        <a href="/p/DEF11111111/">Post 3</a>
        """
        with tempfile.NamedTemporaryFile(mode="w", suffix=".html", delete=False) as f:
            f.write(html)
            file_path = Path(f.name)

        try:
            shortcodes = extract_shortcodes_from_html(file_path)
            assert len(shortcodes) == 3
            assert "ABC12345678" in shortcodes
            assert "XYZ98765432" in shortcodes
            assert "DEF11111111" in shortcodes
        finally:
            file_path.unlink()

    def test_extract_shortcodes_from_reel_urls(self) -> None:
        """Test extracting shortcodes from /reel/ URLs."""
        html = """
        <a href="/reel/REEL1234567/">Reel 1</a>
        <a href="/reel/REEL7654321/">Reel 2</a>
        """
        with tempfile.NamedTemporaryFile(mode="w", suffix=".html", delete=False) as f:
            f.write(html)
            file_path = Path(f.name)

        try:
            shortcodes = extract_shortcodes_from_html(file_path)
            assert len(shortcodes) == 2
            assert "REEL1234567" in shortcodes
        finally:
            file_path.unlink()

    def test_extract_shortcodes_deduplicates(self) -> None:
        """Test that duplicate shortcodes are removed."""
        html = """
        <a href="/p/DUPLICATE11/">First</a>
        <a href="/p/DUPLICATE11/">Second</a>
        <a href="/p/DUPLICATE11/">Third</a>
        """
        with tempfile.NamedTemporaryFile(mode="w", suffix=".html", delete=False) as f:
            f.write(html)
            file_path = Path(f.name)

        try:
            shortcodes = extract_shortcodes_from_html(file_path)
            assert len(shortcodes) == 1
            assert shortcodes[0] == "DUPLICATE11"
        finally:
            file_path.unlink()

    def test_extract_shortcodes_preserves_order(self) -> None:
        """Test that order is preserved."""
        html = """
        <a href="/p/FIRST111111/">First</a>
        <a href="/p/SECOND22222/">Second</a>
        <a href="/p/THIRD333333/">Third</a>
        """
        with tempfile.NamedTemporaryFile(mode="w", suffix=".html", delete=False) as f:
            f.write(html)
            file_path = Path(f.name)

        try:
            shortcodes = extract_shortcodes_from_html(file_path)
            assert shortcodes[0] == "FIRST111111"
            assert shortcodes[1] == "SECOND22222"
            assert shortcodes[2] == "THIRD333333"
        finally:
            file_path.unlink()

    def test_extract_shortcodes_empty_file(self) -> None:
        """Test extraction from empty file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".html", delete=False) as f:
            f.write("")
            file_path = Path(f.name)

        try:
            shortcodes = extract_shortcodes_from_html(file_path)
            assert shortcodes == []
        finally:
            file_path.unlink()


class TestSleepWithJitter:
    """Tests for sleep with jitter function."""

    @patch("src.instagram.time.sleep")
    @patch("src.instagram.random.uniform")
    def test_sleep_with_jitter_calls_sleep(
        self, mock_uniform: MagicMock, mock_sleep: MagicMock
    ) -> None:
        """Test that sleep is called with base + jitter."""
        mock_uniform.return_value = 1.5
        _sleep_with_jitter(5.0)
        mock_sleep.assert_called_once_with(6.5)

    @patch("src.instagram.time.sleep")
    @patch("src.instagram.random.uniform")
    def test_sleep_with_default_base(
        self, mock_uniform: MagicMock, mock_sleep: MagicMock
    ) -> None:
        """Test sleep with default base value."""
        mock_uniform.return_value = 2.0
        _sleep_with_jitter()
        # Default BASE_DELAY_SECONDS is 5.0
        mock_sleep.assert_called_once_with(7.0)


class TestInstagramCrawler:
    """Tests for InstagramCrawler class."""

    @patch("glob.glob")
    @patch("src.instagram.instaloader.Instaloader")
    def test_crawler_tries_session_first(
        self, mock_instaloader: MagicMock, mock_glob: MagicMock
    ) -> None:
        """Test that crawler tries to load session before login."""
        from src.instagram import InstagramCrawler

        mock_loader = MagicMock()
        mock_loader.context = MagicMock()
        mock_instaloader.return_value = mock_loader

        # Mock session loading to fail
        mock_loader.load_session_from_file.side_effect = Exception("No session")
        mock_glob.return_value = []

        with patch("src.instagram.Path.home") as mock_home:
            mock_home.return_value = Path("/fake/home")
            InstagramCrawler("testuser", "testpass")

            # Should have tried to login after session load failed
            mock_loader.login.assert_called_once_with("testuser", "testpass")

    @patch("src.instagram.instaloader.Instaloader")
    def test_crawler_uses_existing_session(self, mock_instaloader: MagicMock) -> None:
        """Test that crawler uses existing session if available."""
        from src.instagram import InstagramCrawler

        mock_loader = MagicMock()
        mock_loader.context = MagicMock()
        mock_instaloader.return_value = mock_loader

        with patch("src.instagram.Path.home") as mock_home:
            mock_home_path = Path(tempfile.mkdtemp())
            mock_home.return_value = mock_home_path

            # Create a fake session file
            session_dir = mock_home_path / ".config" / "instaloader"
            session_dir.mkdir(parents=True)
            session_file = session_dir / "session-testuser"
            session_file.write_text("fake session")

            try:
                InstagramCrawler("testuser", "testpass")

                # Should have loaded session, not logged in
                mock_loader.load_session_from_file.assert_called()
                mock_loader.login.assert_not_called()
            finally:
                session_file.unlink()
                session_dir.rmdir()
                (mock_home_path / ".config").rmdir()
                mock_home_path.rmdir()

    @patch("glob.glob")
    @patch("src.instagram.instaloader.Instaloader")
    def test_handle_rate_limit_exponential_backoff(
        self, mock_instaloader: MagicMock, mock_glob: MagicMock
    ) -> None:
        """Test rate limit handling with exponential backoff."""
        from src.instagram import InstagramCrawler

        mock_loader = MagicMock()
        mock_loader.context = MagicMock()
        mock_instaloader.return_value = mock_loader
        mock_glob.return_value = []

        with patch("src.instagram.Path.home") as mock_home:
            mock_home.return_value = Path("/fake/home")
            with patch("src.instagram.time.sleep"):
                crawler = InstagramCrawler("testuser", "testpass")

                # Test rate limit handling
                with patch("src.instagram.time.sleep") as mock_sleep:
                    result = crawler._handle_rate_limit(0)
                    assert result is True
                    mock_sleep.assert_called_once()

                    # At max retries
                    result = crawler._handle_rate_limit(5)
                    assert result is False

    @patch("glob.glob")
    @patch("src.instagram.instaloader.Instaloader")
    @patch("src.instagram.instaloader.Profile")
    def test_list_videos(
        self,
        mock_profile_class: MagicMock,
        mock_instaloader: MagicMock,
        mock_glob: MagicMock,
    ) -> None:
        """Test listing videos from a profile."""
        from src.instagram import InstagramCrawler

        mock_loader = MagicMock()
        mock_loader.context = MagicMock()
        mock_instaloader.return_value = mock_loader
        mock_glob.return_value = []

        # Mock profile
        mock_profile = MagicMock()
        mock_profile.mediacount = 2
        mock_profile_class.from_username.return_value = mock_profile

        # Mock posts - one video, one non-video
        mock_video_post = MagicMock()
        mock_video_post.shortcode = "VIDEO1"
        mock_video_post.is_video = True
        mock_video_post.video_url = "https://cdn.instagram.com/video1.mp4"
        mock_video_post.typename = "GraphVideo"
        mock_video_post.caption = "Test video"

        mock_photo_post = MagicMock()
        mock_photo_post.shortcode = "PHOTO1"
        mock_photo_post.is_video = False

        mock_profile.get_posts.return_value = iter([mock_video_post, mock_photo_post])

        with patch("src.instagram.Path.home") as mock_home:
            mock_home.return_value = Path("/fake/home")
            with patch("src.instagram.time.sleep"):
                crawler = InstagramCrawler("testuser", "testpass")
                result = crawler.list_videos("test_profile")

        assert result.profile == "test_profile"
        assert len(result.videos) == 1
        assert result.videos[0].shortcode == "VIDEO1"

    @patch("glob.glob")
    @patch("src.instagram.instaloader.Instaloader")
    @patch("src.instagram.instaloader.Profile")
    def test_get_video_posts(
        self,
        mock_profile_class: MagicMock,
        mock_instaloader: MagicMock,
        mock_glob: MagicMock,
    ) -> None:
        """Test iterating over video posts."""
        from src.instagram import InstagramCrawler

        mock_loader = MagicMock()
        mock_loader.context = MagicMock()
        mock_instaloader.return_value = mock_loader
        mock_glob.return_value = []

        mock_profile = MagicMock()
        mock_profile.mediacount = 1

        mock_video = MagicMock()
        mock_video.shortcode = "V1"
        mock_video.is_video = True
        mock_video.video_url = "https://cdn.instagram.com/v1.mp4"
        mock_video.typename = "GraphVideo"
        mock_video.caption = None

        mock_profile.get_posts.return_value = iter([mock_video])
        mock_profile_class.from_username.return_value = mock_profile

        with patch("src.instagram.Path.home") as mock_home:
            mock_home.return_value = Path("/fake/home")
            with patch("src.instagram.time.sleep"):
                crawler = InstagramCrawler("testuser", "testpass")
                videos = list(crawler.get_video_posts("test", skip_shortcodes=set()))

        assert len(videos) == 1
        assert videos[0].shortcode == "V1"

    @patch("glob.glob")
    @patch("src.instagram.instaloader.Instaloader")
    @patch("src.instagram.urllib.request.urlretrieve")
    def test_download_video(
        self,
        mock_urlretrieve: MagicMock,
        mock_instaloader: MagicMock,
        mock_glob: MagicMock,
    ) -> None:
        """Test downloading a video."""
        from src.instagram import InstagramCrawler

        mock_loader = MagicMock()
        mock_loader.context = MagicMock()
        mock_instaloader.return_value = mock_loader
        mock_glob.return_value = []

        with patch("src.instagram.Path.home") as mock_home:
            mock_home.return_value = Path("/fake/home")
            with patch("src.instagram.time.sleep"):
                crawler = InstagramCrawler("testuser", "testpass")
                output_path = Path("/tmp/test_video.mp4")
                result = crawler.download_video(
                    "https://cdn.instagram.com/video.mp4", output_path
                )

        mock_urlretrieve.assert_called_once()
        assert result == output_path

    @patch("glob.glob")
    @patch("src.instagram.instaloader.Instaloader")
    @patch("src.instagram.instaloader.Post")
    def test_get_post_by_shortcode(
        self,
        mock_post_class: MagicMock,
        mock_instaloader: MagicMock,
        mock_glob: MagicMock,
    ) -> None:
        """Test fetching a post by shortcode."""
        from src.instagram import InstagramCrawler

        mock_loader = MagicMock()
        mock_loader.context = MagicMock()
        mock_instaloader.return_value = mock_loader
        mock_glob.return_value = []

        mock_post = MagicMock()
        mock_post.shortcode = "TEST1"
        mock_post.is_video = True
        mock_post.video_url = "https://cdn.instagram.com/test1.mp4"
        mock_post.typename = "GraphVideo"
        mock_post.caption = "Test caption"
        mock_post_class.from_shortcode.return_value = mock_post

        with patch("src.instagram.Path.home") as mock_home:
            mock_home.return_value = Path("/fake/home")
            with patch("src.instagram.time.sleep"):
                crawler = InstagramCrawler("testuser", "testpass")
                result = crawler.get_post_by_shortcode("TEST1")

        assert result is not None
        assert result.shortcode == "TEST1"
        assert result.video_url == "https://cdn.instagram.com/test1.mp4"

    @patch("glob.glob")
    @patch("src.instagram.instaloader.Instaloader")
    @patch("src.instagram.instaloader.Post")
    def test_get_post_by_shortcode_not_video(
        self,
        mock_post_class: MagicMock,
        mock_instaloader: MagicMock,
        mock_glob: MagicMock,
    ) -> None:
        """Test fetching a non-video post returns None."""
        from src.instagram import InstagramCrawler

        mock_loader = MagicMock()
        mock_loader.context = MagicMock()
        mock_instaloader.return_value = mock_loader
        mock_glob.return_value = []

        mock_post = MagicMock()
        mock_post.shortcode = "PHOTO1"
        mock_post.is_video = False
        mock_post_class.from_shortcode.return_value = mock_post

        with patch("src.instagram.Path.home") as mock_home:
            mock_home.return_value = Path("/fake/home")
            with patch("src.instagram.time.sleep"):
                crawler = InstagramCrawler("testuser", "testpass")
                result = crawler.get_post_by_shortcode("PHOTO1")

        assert result is None

    @patch("glob.glob")
    @patch("src.instagram.instaloader.Instaloader")
    def test_get_video_url_sidecar(
        self, mock_instaloader: MagicMock, mock_glob: MagicMock
    ) -> None:
        """Test getting video URL from GraphSidecar post."""
        from src.instagram import InstagramCrawler

        mock_loader = MagicMock()
        mock_loader.context = MagicMock()
        mock_instaloader.return_value = mock_loader
        mock_glob.return_value = []

        with patch("src.instagram.Path.home") as mock_home:
            mock_home.return_value = Path("/fake/home")
            with patch("src.instagram.time.sleep"):
                crawler = InstagramCrawler("testuser", "testpass")

                # Test GraphSidecar with video
                mock_sidecar_post = MagicMock()
                mock_sidecar_post.typename = "GraphSidecar"

                mock_video_node = MagicMock()
                mock_video_node.is_video = True
                mock_video_node.video_url = (
                    "https://cdn.instagram.com/sidecar_video.mp4"
                )

                mock_photo_node = MagicMock()
                mock_photo_node.is_video = False

                mock_sidecar_post.get_sidecar_nodes.return_value = [
                    mock_photo_node,
                    mock_video_node,
                ]

                result = crawler._get_video_url(mock_sidecar_post)
                assert result == "https://cdn.instagram.com/sidecar_video.mp4"
