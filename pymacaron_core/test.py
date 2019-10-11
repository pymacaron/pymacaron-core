def return_token(*args):
    # Mocked anyway
    pass

# Dummy implementation of model persistence
class PersistentFoo():

    @staticmethod
    def load_from_db():
        # Load object(s) from storage
        return 'bob'

    def save_to_db(object):
        # Put object into storage
        assert isinstance(object, PersistentFoo)
        return 'foo'


# Dummy implementation of model inheritance
class FunnyGrandad():

    def roflol(self):
        return 'roflol'

class FunnyDad(FunnyGrandad):

    def lol(self):
        return 'lol'
