from django.core import mail
from django.core.cache import cache
from django.test import TestCase, override_settings

from .models.users2 import User2
from .utils.captcha import CAPTCHA_CACHE_PREFIX, verify_captcha


@override_settings(
    CACHES={'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'registration-tests',
    }},
    EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
)
class RegistrationCaptchaTests(TestCase):
    def test_email_send_preserves_captcha_for_registration(self):
        cache.set(CAPTCHA_CACHE_PREFIX + 'register-test', 'ABCD')
        captcha = {'captcha_id': 'register-test', 'captcha_text': 'ABCD'}
        email = 'registration@example.com'

        sent = self.client.post('/api/auth/send-code/', {'email': email, **captcha})
        self.assertEqual(sent.json()['code'], 0)

        reused = self.client.post('/api/auth/send-code/', {
            'email': 'another@example.com', **captcha,
        })
        self.assertEqual(reused.json()['code'], 4101)
        self.assertEqual(len(mail.outbox), 1)
        code = mail.outbox[0].body.splitlines()[0].removeprefix('您本次的验证码是：').rstrip('。')

        registered = self.client.post('/api/auth/register/', {
            'email': email,
            'username': 'registration_test',
            'password': 'test-password',
            'email_code': code,
            **captcha,
        })
        self.assertEqual(registered.json()['code'], 0)
        self.assertTrue(User2.objects.filter(email=email).exists())
        self.assertFalse(verify_captcha(captcha['captcha_id'], captcha['captcha_text']))
