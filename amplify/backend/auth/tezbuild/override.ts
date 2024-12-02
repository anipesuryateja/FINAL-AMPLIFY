import { AmplifyAuthCognitoStackTemplate } from '@aws-amplify/cli-extensibility-helper'

export function override(resources: AmplifyAuthCognitoStackTemplate) {
    const myCustomAttribute = {
        attributeDataType: 'String',
        developerOnlyAttribute: false,
        mutable: true,
        name: 'Role',
        required: true,
    }
    resources.userPool.schema = [
        ...(resources.userPool.schema as any[]), // Carry over existing attributes (example: email)
        myCustomAttribute,
    ]
}