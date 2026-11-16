from nudge import config


def test_installed_config_reads_working_directory_env(tmp_path, monkeypatch):
    settings = tmp_path / '.env'
    settings.write_text('TYPESAFE_API_KEY=local-key\nWAKE_WORD=models/custom.onnx\n')
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(config, 'ROOT', tmp_path / 'site-packages')
    monkeypatch.delenv('TYPESAFE_API_KEY', raising=False)
    monkeypatch.delenv('WAKE_WORD', raising=False)
    loaded = config.load_config()
    assert loaded.typesafe_api_key == 'local-key'
    assert loaded.wake_word == str(tmp_path / 'models' / 'custom.onnx')


def test_environment_overrides_env_file(tmp_path, monkeypatch):
    (tmp_path / '.env').write_text('TYPESAFE_API_KEY=file-key\n')
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv('TYPESAFE_API_KEY', 'environment-key')
    assert config.load_config().typesafe_api_key == 'environment-key'


def test_source_config_falls_back_to_project_env(tmp_path, monkeypatch):
    project = tmp_path / 'project'
    project.mkdir()
    (project / '.env').write_text('TYPESAFE_API_KEY=project-key\nWAKE_WORD=models/custom.onnx\n')
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(config, 'ROOT', project)
    monkeypatch.delenv('TYPESAFE_API_KEY', raising=False)
    monkeypatch.delenv('WAKE_WORD', raising=False)
    loaded = config.load_config()
    assert loaded.typesafe_api_key == 'project-key'
    assert loaded.wake_word == str(project / 'models' / 'custom.onnx')


def test_environment_model_path_uses_working_directory_without_env_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(config, 'ROOT', tmp_path / 'site-packages')
    monkeypatch.setenv('WAKE_WORD', 'models/custom.onnx')
    assert config.load_config().wake_word == str(tmp_path / 'models' / 'custom.onnx')
