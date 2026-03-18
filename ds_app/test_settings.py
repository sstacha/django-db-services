from ubercode.utils.environment import Environment, ColorLogger
from ubercode.utils.convert import to_str

from ds.settings import ALLOWED_HOSTS


def test_settings():
    ENV_SETTINGS = {
        'BOOGER': 'booger',
        'DOCROOTCMS_BOOGER2': 'booger2',
        'DOCROOTCMS_ALLOWED_HOSTS': '*, localhost, 127.0.0.1',
    }
    slog = ColorLogger("test_settings", "DEBUG")
    mask_props = Environment.DEFAULT_SECRET_PROPERTIES + ('AUTH_LDAP_BIND_PASSWORD',
                                                          'DOCROOTCMS_AUTH_LDAP_BIND_PASSWORD')
    settings_environment = Environment(slog, secret_properties=mask_props,
                                       environment_variable_map=ENV_SETTINGS)

    # test that we get an empty set with no values set
    ALLOWED_HOSTS = settings_environment.override_variable("ALLOWED_HOSTS", getattr('ALLOWED_HOST'))
    env_allowed_hosts_str = to_str(settings_environment.override_variable("ALLOWED_HOSTS"))
    # NOTE: default allowed_hosts of [] = ['.localhost', '127.0.0.1', '[::1]'] in current Django versions
    # NOTE: can still use * to bypass any checks but not recommended anymore even for development
    # best practice,  use nothing or etc/hosts value like app.localhost for development and a list for deployment to servers
    # ALLOWED_HOSTS = list((host.strip() for host in env_allowed_hosts_str.split(',') if host))
    ALLOWED_HOSTS = [host.strip() for host in env_allowed_hosts_str.split(',') if host]
    env_csrf_trusted_origins_str = to_str(settings_environment.override_variable("CSRF_TRUSTED_ORIGINS"))
    # NOTE: much like cors you only need csrf if cross domain and unsafe methods like POST, PUT, DELETE
    # NOTE: trusted_origins require scheme and need * placeholder; allowed hosts cant have scheme and lead with dot.
    # ex: [https://*.example.com] vs [.example.com]
    CSRF_TRUSTED_ORIGINS = [origin.strip() for origin in env_csrf_trusted_origins_str.split(',') if origin]

    # test that empty string results in empty list -> [] or rethink the split stuff
    slog.debug(f"allowed hosts: {ALLOWED_HOSTS}")
    slog.debug(f"trusted origins: {CSRF_TRUSTED_ORIGINS}")

    assert(isinstance(ALLOWED_HOSTS, list))
    assert(str(ALLOWED_HOSTS) != "['']")
    assert(isinstance(CSRF_TRUSTED_ORIGINS, list))
    assert (str(CSRF_TRUSTED_ORIGINS) != "['']")



